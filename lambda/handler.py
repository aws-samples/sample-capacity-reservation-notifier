import boto3
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict

def lambda_handler(event, context):
    """扫描所有 regions 的 active Capacity Reservations 并发送邮件通知"""
    try:
        sns_topic_arn = os.environ['SNS_TOPIC_ARN']
        
        # 获取所有 regions
        regions = get_all_regions()
        print(f"扫描 {len(regions)} 个 regions")
        
        # 扫描所有 regions 的 Capacity Reservations
        all_reservations = []
        for region in regions:
            reservations = get_capacity_reservations(region)
            all_reservations.extend(reservations)
        
        print(f"找到 {len(all_reservations)} 个 active Capacity Reservations")

        # 查询每个 CB 匹配的已开机 EC2
        cb_instances = get_running_instances_for_reservations(all_reservations)

        # 生成邮件内容
        subject, body = generate_email(all_reservations, cb_instances)
        
        # 发送邮件
        send_email(sns_topic_arn, subject, body)
        
        return {
            'statusCode': 200,
            'body': f'成功扫描 {len(regions)} 个 regions，找到 {len(all_reservations)} 个 active reservations'
        }
    
    except Exception as e:
        print(f"错误: {str(e)}")
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
        except:
            pass
        raise

def get_all_regions() -> List[str]:
    """获取所有可用的 AWS regions"""
    ec2 = boto3.client('ec2')
    response = ec2.describe_regions()
    return [region['RegionName'] for region in response['Regions']]

def get_capacity_reservations(region: str) -> List[Dict]:
    """获取指定 region 的 active Capacity Reservations（处理分页）"""
    ec2 = boto3.client('ec2', region_name=region)
    
    try:
        reservations = []
        next_token = None
        
        while True:
            params = {
                'MaxResults': 100
            }
            
            if next_token:
                params['NextToken'] = next_token
            
            response = ec2.describe_capacity_reservations(**params)
            
            for reservation in response['CapacityReservations']:
                reservation['Region'] = region
                reservations.append(reservation)
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        return reservations
    
    except Exception as e:
        print(f"扫描 region {region} 时出错: {str(e)}")
        return []

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

def get_running_instances_for_reservations(reservations: List[Dict]) -> Dict[str, List[Dict]]:
    """查询每个 CB 关联的已开机 EC2 实例"""
    # 按 region 分组 reservation id
    by_region: Dict[str, List[str]] = {}
    for res in reservations:
        region = res['Region']
        by_region.setdefault(region, []).append(res['CapacityReservationId'])

    result: Dict[str, List[Dict]] = {}
    for region, cr_ids in by_region.items():
        ec2 = boto3.client('ec2', region_name=region)
        try:
            paginator = ec2.get_paginator('describe_instances')
            for page in paginator.paginate(
                Filters=[
                    {'Name': 'capacity-reservation-id', 'Values': cr_ids},
                    {'Name': 'instance-state-name', 'Values': ['running']},
                ]
            ):
                for reservation in page['Reservations']:
                    for inst in reservation['Instances']:
                        cr_id = inst.get('CapacityReservationId') or \
                                inst.get('CapacityReservationSpecification', {}) \
                                    .get('CapacityReservationTarget', {}) \
                                    .get('CapacityReservationId')
                        if cr_id:
                            result.setdefault(cr_id, []).append(inst)
        except Exception as e:
            print(f"查询 region {region} EC2 实例时出错: {str(e)}")
    return result

def send_email(topic_arn: str, subject: str, body: str):
    """通过 SNS 发送邮件"""
    sns = boto3.client('sns')
    sns.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=body,
        MessageStructure='string'
    )
    print(f"邮件已发送: {subject}")
