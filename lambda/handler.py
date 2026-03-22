import boto3
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict

# Import shared EC2 service functions
from common.ec2_service import (
    get_all_regions,
    get_capacity_reservations,
    get_running_instances_for_reservations
)
from common.mock_data import (
    get_mock_regions,
    generate_mock_reservations,
    get_mock_running_instances_for_reservations
)

def lambda_handler(event, context):
    """扫描所有 regions 的 active Capacity Reservations 并发送邮件通知"""
    import traceback
    beijing_tz = timezone(timedelta(hours=8))
    start_time = datetime.now(timezone.utc)
    print(f"[START] lambda_handler invoked | event={event} | time={start_time.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')}")

    try:
        sns_topic_arn = os.environ['SNS_TOPIC_ARN']
        mode = event.get('mode', 'daily_report') if event else 'daily_report'
        print(f"[CONFIG] mode={mode} | sns_topic_arn={sns_topic_arn}")

        # Check if mock mode is enabled
        use_mock_data = os.environ.get('ENABLE_MOCK_DATA', 'false').lower() == 'true'
        print(f"[CONFIG] use_mock_data={use_mock_data}")

        if use_mock_data:
            print("[MOCK] Mock模式已启用 - 使用模拟数据生成邮件报告")
            all_reservations = generate_mock_reservations()
            cb_instances = get_mock_running_instances_for_reservations(all_reservations)
            region_count = len(set(r['Region'] for r in all_reservations))
        else:
            # 获取所有 regions
            regions = get_all_regions()
            print(f"[SCAN] 扫描 {len(regions)} 个 regions: {regions}")

            # 扫描所有 regions 的 Capacity Reservations
            all_reservations = []
            for region in regions:
                reservations = get_capacity_reservations(region)
                if reservations:
                    print(f"[SCAN] {region}: 找到 {len(reservations)} 个 CB")
                all_reservations.extend(reservations)

            print(f"[SCAN] 汇总: 共找到 {len(all_reservations)} 个 active Capacity Reservations")
            for r in all_reservations:
                print(f"[CB] id={r.get('CapacityReservationId')} region={r.get('Region')} state={r.get('State')} "
                      f"type={r.get('InstanceType')} total={r.get('TotalInstanceCount')} "
                      f"start={r.get('StartDate')} end={r.get('EndDate')}")

            # 查询每个 CB 匹配的已开机 EC2
            print("[SCAN] 查询各 CB 运行中的 EC2 实例...")
            cb_instances = get_running_instances_for_reservations(all_reservations)
            for rid, instances in cb_instances.items():
                if instances:
                    print(f"[EC2] CB {rid} 有 {len(instances)} 台运行中实例: {[i['InstanceId'] for i in instances]}")
            region_count = len(regions)

        if mode == 'alert_check':
            print("[MODE] 告警检查模式 - 仅发送紧急告警邮件")
            check_and_send_urgent_alerts(all_reservations, cb_instances, sns_topic_arn)
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"[END] alert_check 完成 | 耗时 {elapsed:.1f}s")
            return {
                'statusCode': 200,
                'body': f'告警检查完成，扫描 {len(all_reservations)} 个 reservations'
            }
        else:
            print("[MODE] 日报模式 - 生成并发送汇总邮件")
            # 生成邮件内容
            subject, body = generate_email(all_reservations, cb_instances)
            print(f"[EMAIL] 生成邮件完成 | subject={subject} | body_length={len(body)}")

            # 发送邮件
            send_email(sns_topic_arn, subject, body)

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"[END] daily_report 完成 | 耗时 {elapsed:.1f}s")
            return {
                'statusCode': 200,
                'body': f'成功扫描 {region_count} 个 regions，找到 {len(all_reservations)} 个 active reservations'
            }

    except Exception as e:
        print(f"[ERROR] 异常发生: {str(e)}")
        print("[ERROR] Traceback: " + traceback.format_exc())
        # 发送错误通知
        try:
            beijing_tz = timezone(timedelta(hours=8))
            beijing_now = datetime.now(beijing_tz)
            error_timestamp = beijing_now.strftime('%Y-%m-%d %H:%M:%S CST')
            error_subject = f"Capacity Reservation Notifier - Error - {error_timestamp}"
            error_body = f"""Capacity Reservation Notifier - Error Report
{'=' * 80}

Time: {error_timestamp}

Error: {str(e)}

{'=' * 80}
"""
            send_email(os.environ['SNS_TOPIC_ARN'], error_subject, error_body)
        except Exception as e2:
            print(f"[ERROR] 错误通知邮件发送失败: {str(e2)}")
        raise


def check_and_send_urgent_alerts(reservations: List[Dict], cb_instances: Dict[str, List[Dict]], sns_topic_arn: str):
    """检查即将开机/关机的 CB，发送独立告警邮件"""
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(timezone.utc)
    one_hour_later = now + timedelta(hours=1)
    two_hours_later = now + timedelta(hours=2)
    print(f"[ALERT] 检查窗口: now={now.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')} "
          f"launch_window=1h shutdown_window=2h")

    def res_name(r):
        name_tag = next((t['Value'] for t in r.get('Tags', []) if t['Key'] == 'Name'), None)
        return name_tag or r['CapacityReservationId']

    # 即将开机：StartDate 在 (now, now+2h]
    launch_soon = [r for r in reservations
                   if r.get('StartDate') and now < r['StartDate'] <= two_hours_later]
    print(f"[ALERT] 即将开机(2h内): {len(launch_soon)} 个 CB")
    for r in launch_soon:
        print(f"[ALERT]   LAUNCH: {r.get('CapacityReservationId')} start={r.get('StartDate')}")

    # 即将到期：EndDate 在 (now, now+2h]，且 State=active
    shutdown_soon = [r for r in reservations
                     if r.get('EndDate') and now < r['EndDate'] <= two_hours_later
                     and r.get('State', '').lower() == 'active']
    print(f"[ALERT] 即将到期(2h内): {len(shutdown_soon)} 个 CB")
    for r in shutdown_soon:
        print(f"[ALERT]   SHUTDOWN: {r.get('CapacityReservationId')} end={r.get('EndDate')} state={r.get('State')}")

    W = 80

    # 每个即将开机的 CB 发一封独立告警邮件
    for r in launch_soon:
        rid       = r.get('CapacityReservationId', 'N/A')
        name      = res_name(r)
        region    = r.get('Region', 'N/A')
        az        = r.get('AvailabilityZone', 'N/A')
        itype     = r.get('InstanceType', 'N/A')
        count     = r.get('TotalInstanceCount', 'N/A')
        start_cst = r['StartDate'].astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')
        now_cst   = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')
        console_url = f"https://console.aws.amazon.com/ec2/v2/home?region={region}#CapacityReservations:"

        subject = f"[ACTION: LAUNCH REQUIRED] {region} | {rid} starts at {start_cst[:19]}"

        lines = []
        lines.append("*" * W)
        lines.append(f"  [ACTION: LAUNCH REQUIRED] - Region: {region} | CB 即将开始，请立即启动 EC2 实例")
        lines.append(f"  Console链接: {console_url}")
        lines.append("*" * W)
        lines.append("")
        lines.append(f"  告警时间  : {now_cst} (北京时间)")
        lines.append(f"  CB 开始时间: {start_cst} (北京时间)")
        lines.append("")
        lines.append("-" * W)
        lines.append(f"  CB ID         : {rid}" + (f"  [{name}]" if name != rid else ""))
        lines.append(f"  Region        : {region}")
        lines.append(f"  Avail Zone    : {az}")
        lines.append(f"  Instance Type : {itype}")
        lines.append(f"  Instance Count: {count}")
        lines.append(f"  Start Time    : {start_cst} (北京时间)")
        running = cb_instances.get(rid, [])
        if running:
            lines.append(f"  Running EC2s  : {', '.join(i['InstanceId'] for i in running)}")
        lines.append("-" * W)
        lines.append("")
        lines.append(f"  !! 请在 {start_cst} (北京时间) 前启动 {count} 台 {itype} 实例 !!")
        lines.append(f"     CB 将于该时间开始，请确保实例已提前在对应 AZ ({az}) 启动。")
        lines.append("")
        lines.append("*" * W)

        send_email(sns_topic_arn, subject, '\n'.join(lines))
        print(f"开机告警已发送: {rid} 开始时间 {start_cst}")

    # 每个即将到期的 CB 发一封独立告警邮件
    for r in shutdown_soon:
        rid     = r.get('CapacityReservationId', 'N/A')
        name    = res_name(r)
        region  = r.get('Region', 'N/A')
        az      = r.get('AvailabilityZone', 'N/A')
        itype   = r.get('InstanceType', 'N/A')
        count   = r.get('TotalInstanceCount', 'N/A')
        end_cst = r['EndDate'].astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')
        now_cst = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')
        console_url = f"https://console.aws.amazon.com/ec2/v2/home?region={region}#CapacityReservations:"

        subject = f"[ACTION: SHUTDOWN REQUIRED] {region} | {rid} expires at {end_cst[:19]}"

        lines = []
        lines.append("*" * W)
        lines.append(f"  [ACTION: SHUTDOWN REQUIRED] - Region: {region} | CB 即将到期，请立即完成实例迁移/关机")
        lines.append(f"  Console链接: {console_url}")
        lines.append("*" * W)
        lines.append("")
        lines.append(f"  告警时间  : {now_cst} (北京时间)")
        lines.append(f"  CB 到期时间: {end_cst} (北京时间)")
        lines.append("")
        lines.append("-" * W)
        lines.append(f"  CB ID         : {rid}" + (f"  [{name}]" if name != rid else ""))
        lines.append(f"  Region        : {region}")
        lines.append(f"  Avail Zone    : {az}")
        lines.append(f"  Instance Type : {itype}")
        lines.append(f"  Instance Count: {count}")
        lines.append(f"  End Time      : {end_cst} (北京时间)")
        running = cb_instances.get(rid, [])
        if running:
            lines.append(f"  Running EC2s  : {', '.join(i['InstanceId'] for i in running)}")
        else:
            lines.append(f"  Running EC2s  : none")
        lines.append("-" * W)
        lines.append("")
        lines.append(f"  !! 请在 {end_cst} (北京时间) 前完成实例迁移/关机，CB 将于该时间回收 !!")
        lines.append(f"     到期后 CB 将被释放，请确保运行中的实例已完成迁移或关机。")
        lines.append("")
        lines.append("*" * W)

        send_email(sns_topic_arn, subject, '\n'.join(lines))
        print(f"关机告警已发送: {rid} 到期时间 {end_cst}")

    if not launch_soon and not shutdown_soon:
        print("无紧急告警")


def generate_email(reservations: List[Dict], cb_instances: Dict[str, List[Dict]] = None) -> tuple:
    """生成邮件主题和纯文本内容"""
    # 北京时间 (UTC+8)
    beijing_tz = timezone(timedelta(hours=8))
    beijing_now = datetime.now(beijing_tz)
    timestamp = beijing_now.strftime('%Y-%m-%d %H:%M:%S CST')
    subject = f"Capacity Reservation Report - {timestamp}"

    active_reservation = 0

    # 简报提醒
    now = datetime.now(timezone.utc)
    alerts = []

    def res_name(r):
        name_tag = next((t['Value'] for t in r.get('Tags', []) if t['Key'] == 'Name'), None)
        return name_tag or r['CapacityReservationId']

    starting_soon = [r for r in reservations
                     if r.get('StartDate') and now < r['StartDate'] <= now + timedelta(hours=24)]
    if starting_soon:
        alerts.append(f"[STARTING SOON] {len(starting_soon)} reservations approaching start time")
        for r in starting_soon:
            alerts.append(f"  - {res_name(r)} ({r['Region']}): {r['StartDate'].astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M CST')}")

    not_fully_started = [r for r in reservations
                         if r.get('StartDate') and r['StartDate'] <= now
                         and r.get('AvailableInstanceCount', 0) > 0]
    if not_fully_started:
        alerts.append(f"[NOT FULLY LAUNCHED] {len(not_fully_started)} reservations started but not fully launched")
        for r in not_fully_started:
            total = r.get('TotalInstanceCount', 0)
            available = r.get('AvailableInstanceCount', 0)
            alerts.append(f"  - {res_name(r)} ({r['Region']}): total {total} / 【***not launched {available}***】")

    expiring_soon = [r for r in reservations
                     if r.get('EndDate') and now < r['EndDate'] <= now + timedelta(days=2)
                     and r.get('State', '').lower() == 'active']
    if expiring_soon:
        alerts.append(f"[EXPIRING SOON] {len(expiring_soon)} reservations approaching end time")
        for r in expiring_soon:
            alerts.append(f"  - {res_name(r)} ({r['Region']}): {r['EndDate'].astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M CST')}")

    if alerts:
        subject = f"[ACTION REQUIRED] {subject}"
        print("Alert Summary:\n" + "\n".join(alerts))

    if not reservations:
        body = f"""Capacity Reservation Report
{'=' * 80}

Time: {timestamp}

No active Capacity Reservations found.
"""
        return subject, body
    
    # 按 region 分组
    by_region = {}
    for res in reservations:
        region = res['Region']
        if region not in by_region:
            by_region[region] = []
        by_region[region].append(res)
        if res.get('State', '').lower() == 'active':
            active_reservation = active_reservation + 1
    
    # 对每个 region 的 reservations 按 EndDate 排序
    two_days_later = now + timedelta(days=2)
    
    for region in by_region:
        # 按 EndDate 排序，没有 EndDate 的放在最后
        by_region[region].sort(key=lambda x: x.get('EndDate') or datetime.max.replace(tzinfo=timezone.utc))
    
    # 生成纯文本报告
    W = 80
    lines = []

    # Header
    lines.append("*" * W)
    lines.append(f"  AWS CAPACITY RESERVATION REPORT")
    lines.append(f"  Generated : {timestamp}")
    lines.append(f"  Regions   : {len(by_region)}   Total: {len(reservations)}   Active: {active_reservation}")
    lines.append("*" * W)

    # Alert Summary
    if alerts:
        lines.append("")
        lines.append("")
        lines.append("")
        lines.append("")
        lines.append("")
        lines.append("-" * W)
        lines.append("  !! ALERT SUMMARY !!")
        lines.append("-" * W)
        section = None
        for alert in alerts:
            if alert.startswith("["):
                if section:
                    lines.append("")
                section = alert
                lines.append(f"  >>> {alert}")
            else:
                lines.append(f"      {alert}")
        lines.append("-" * W)

    # Per-region details
    for region in sorted(by_region.keys()):
        region_reservations = by_region[region]
        lines.append("")
        lines.append("")
        lines.append("")
        lines.append("")
        lines.append("=" * W)
        lines.append(f"  REGION: {region}  ({len(region_reservations)} reservations)")
        lines.append("=" * W)

        for res in region_reservations:
            print(res)
            rid        = res.get('CapacityReservationId', 'N/A')
            name_tag   = next((t['Value'] for t in res.get('Tags', []) if t['Key'] == 'Name'), None)
            state      = res.get('State', 'N/A').upper()
            itype      = res.get('InstanceType', 'N/A')
            az         = res.get('AvailabilityZone', 'N/A')
            total      = res.get('TotalInstanceCount', 'N/A')
            available  = res.get('AvailableInstanceCount', 0)

            lines.append(f"  +- {rid}" + (f"  [{name_tag}]" if name_tag else ""))
            lines.append(f"  |  State          : {state}")
            lines.append(f"  |  Instance Type  : {itype}")
            lines.append(f"  |  Avail Zone     : {az}")
            lines.append(f"  |  Total / Avail  : {total} / " +
                         (f"*** {available} UNUSED ***" if available > 0 else str(available)))

            start_date = res.get('StartDate')
            lines.append(f"  |  Start Date     : " +
                         (start_date.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST') if start_date else 'N/A'))

            end_date = res.get('EndDate')
            if end_date:
                end_str = end_date.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')
                if end_date <= two_days_later and res.get('State', '').lower() == 'active':
                    end_str = f"*** {end_str}  <-- EXPIRING SOON ***"
                lines.append(f"  |  End Date       : {end_str}")
            else:
                lines.append(f"  |  End Date       : N/A")

            tags = res.get('Tags', [])
            tags_str = ', '.join(f"{t['Key']}={t['Value']}" for t in tags) if tags else 'N/A'
            lines.append(f"  |  Tags           : {tags_str}")

            running = (cb_instances or {}).get(rid, [])
            if running:
                lines.append(f"  |  Running EC2s   : {', '.join(i['InstanceId'] for i in running)}")
            else:
                lines.append(f"  |  Running EC2s   :  none")
            lines.append(f"  +" + "-" * (W - 3))

    lines.append("")
    lines.append("*" * W)
    lines.append("  END OF REPORT")
    lines.append("*" * W)
    
    body = '\n'.join(lines)
    return subject, body


def send_email(topic_arn: str, subject: str, body: str):
    """通过 SNS 发送邮件"""
    # SNS Subject 只允许 ASCII 字符且最长 100 字符
    safe_subject = ''.join(c for c in subject if ord(c) < 128)[:100]
    print(f"[DEBUG] subject raw={repr(subject)} safe={repr(safe_subject)}")
    sns = boto3.client('sns')
    sns.publish(
        TopicArn=topic_arn,
        Subject=safe_subject,
        Message=body,
        MessageStructure='string'
    )
    print(f"邮件已发送: {safe_subject}")
