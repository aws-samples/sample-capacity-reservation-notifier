"""
API Lambda Handler

Handles API Gateway requests for the Capacity Reservation Dashboard.
Provides REST API endpoints for querying reservations and instances.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from common.ec2_service import (
    get_all_regions,
    query_all_reservations_parallel,
    get_instances_by_reservation_id
)
from common.status_calculator import enrich_reservation_with_status
from common.mock_data import (
    generate_mock_reservations,
    generate_mock_instances
)


def format_response(status_code: int, data: dict) -> dict:
    """
    Format successful response with CORS headers

    Args:
        status_code: HTTP status code
        data: Response data dictionary

    Returns:
        API Gateway response format
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # TODO: Change to Amplify domain in production
            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Api-Key'
        },
        'body': json.dumps(data, default=str)
    }


def format_error_response(status_code: int, error_code: str, message: str) -> dict:
    """
    Format error response with CORS headers

    Args:
        status_code: HTTP status code
        error_code: Application error code
        message: Error message

    Returns:
        API Gateway error response format
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Api-Key'
        },
        'body': json.dumps({
            'error': {
                'code': error_code,
                'message': message
            }
        })
    }


def get_all_capacity_reservations() -> Dict[str, Any]:
    """
    Scan all regions for Capacity Reservations and group by region

    Returns:
        Dictionary with regions, reservations, and summaries
    """
    # Check if mock mode is enabled
    use_mock_data = os.environ.get('ENABLE_MOCK_DATA', 'false').lower() == 'true'

    if use_mock_data:
        print("🎭 Mock模式已启用 - 返回模拟数据")
        all_reservations = generate_mock_reservations()
    else:
        print("开始扫描所有 regions 的 Capacity Reservations")
        # Query all reservations in parallel
        all_reservations = query_all_reservations_parallel(max_workers=10)

    print(f"共找到 {len(all_reservations)} 个 Capacity Reservations")

    # Enrich with status information
    now = datetime.now(timezone.utc)
    enriched_reservations = [
        enrich_reservation_with_status(res, now)
        for res in all_reservations
    ]

    # Group by region
    by_region: Dict[str, List[Dict]] = {}
    for res in enriched_reservations:
        region = res['Region']
        if region not in by_region:
            by_region[region] = []
        by_region[region].append(res)

    # Sort reservations within each region by EndDate
    for region in by_region:
        by_region[region].sort(
            key=lambda x: x.get('EndDate') or datetime.max.replace(tzinfo=timezone.utc)
        )

    # Build region data with summaries
    regions_data = []
    total_by_status = {
        'expired': 0,
        'not_fully_launched': 0,
        'expiring_soon': 0,
        'starting_soon': 0,
        'normal': 0
    }

    for region_name in sorted(by_region.keys()):
        reservations = by_region[region_name]

        # Calculate region summary
        region_summary = {
            'total': len(reservations),
            'expired': 0,
            'not_fully_launched': 0,
            'expiring_soon': 0,
            'starting_soon': 0,
            'normal': 0
        }

        for res in reservations:
            # Use all statuses (a CB can have multiple concurrent statuses)
            for status in res.get('statuses', [res['status']]):
                if status in region_summary:
                    region_summary[status] += 1
                if status in total_by_status:
                    total_by_status[status] += 1

        regions_data.append({
            'regionName': region_name,
            'reservations': reservations,
            'summary': region_summary
        })

    # Beijing time
    beijing_tz = timezone(timedelta(hours=8))
    timestamp_utc = datetime.now(timezone.utc)
    timestamp_local = timestamp_utc.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')

    return {
        'regions': regions_data,
        'summary': {
            'totalRegions': len(by_region),
            'totalReservations': len(enriched_reservations),
            'byStatus': total_by_status
        },
        'timestamp': timestamp_utc.isoformat(),
        'timestampLocal': timestamp_local
    }


def get_reservation_instances(reservation_id: str, region: str) -> Dict[str, Any]:
    """
    Get running EC2 instances for a specific Capacity Reservation

    Args:
        reservation_id: Capacity Reservation ID
        region: AWS region name

    Returns:
        Dictionary with instances and summary
    """
    # Check if mock mode is enabled
    use_mock_data = os.environ.get('ENABLE_MOCK_DATA', 'false').lower() == 'true'

    if use_mock_data:
        print(f"🎭 Mock模式已启用 - 返回 {reservation_id} 的模拟实例数据")
        instances = generate_mock_instances(reservation_id, region)
    else:
        print(f"查询 Capacity Reservation {reservation_id} 在 region {region} 的实例")
        instances = get_instances_by_reservation_id(reservation_id, region)

    print(f"找到 {len(instances)} 个运行中的实例")

    # Extract relevant instance information
    instance_list = []
    for inst in instances:
        instance_info = {
            'instanceId': inst.get('InstanceId'),
            'instanceType': inst.get('InstanceType'),
            'state': inst.get('State', {}).get('Name'),
            'privateIpAddress': inst.get('PrivateIpAddress'),
            'publicIpAddress': inst.get('PublicIpAddress'),
            'launchTime': inst.get('LaunchTime').isoformat() if inst.get('LaunchTime') else None,
            'availabilityZone': inst.get('Placement', {}).get('AvailabilityZone'),
            'tags': [
                {'key': tag.get('Key'), 'value': tag.get('Value')}
                for tag in inst.get('Tags', [])
            ]
        }

        # Extract Name tag if exists
        name_tag = next(
            (tag['Value'] for tag in inst.get('Tags', []) if tag.get('Key') == 'Name'),
            None
        )
        if name_tag:
            instance_info['name'] = name_tag

        instance_list.append(instance_info)

    return {
        'reservationId': reservation_id,
        'region': region,
        'instances': instance_list,
        'summary': {
            'total': len(instance_list),
            'running': len([i for i in instance_list if i['state'] == 'running'])
        }
    }




def ensure_eventbridge_forwarding(ec2_region: str, main_sns_account: str, main_event_bus_arn: str) -> None:
    """
    在 EC2 region 建立 EventBridge 规则，将 CloudWatch Alarm 状态变更事件
    跨 region 转发到主 event bus（us-west-2），由主 bus 触发 SNS。
    """
    import boto3
    eb = boto3.client('events', region_name=ec2_region)
    rule_name = 'capacity-reservation-forward-alarm-events'
    target_id = 'ForwardToMainBus'

    # 创建/更新规则：监听 CloudWatch Alarm 状态变更
    eb.put_rule(
        Name=rule_name,
        EventPattern='{"source":["aws.cloudwatch"],"detail-type":["CloudWatch Alarm State Change"],"detail":{"alarmName":[{"prefix":"capacity-reservation-status-check-"}]}}',
        State='ENABLED',
        Description='Forward capacity-reservation alarm events to main event bus'
    )
    print(f"[ALARM] EventBridge rule created/updated in {ec2_region}")

    # 目标：转发到主 region event bus
    eb.put_targets(
        Rule=rule_name,
        Targets=[{
            'Id': target_id,
            'Arn': main_event_bus_arn,
            'RoleArn': f"arn:aws:iam::{main_sns_account}:role/capacity-reservation-eventbridge-forward-role"
        }]
    )
    print(f"[ALARM] EventBridge target set: {main_event_bus_arn}")


def ensure_main_bus_sns_rule(main_region: str, sns_topic_arn: str) -> None:
    """
    在主 region event bus 上建立规则：
    接收跨 region 转发的告警事件 → 触发 SNS。
    """
    import boto3
    eb = boto3.client('events', region_name=main_region)
    rule_name = 'capacity-reservation-alarm-to-sns'

    eb.put_rule(
        Name=rule_name,
        EventPattern='{"source":["aws.cloudwatch"],"detail-type":["CloudWatch Alarm State Change"],"detail":{"alarmName":[{"prefix":"capacity-reservation-status-check-"}],"state":{"value":["ALARM"]}}}',
        State='ENABLED',
        Description='Send capacity-reservation alarm notifications to SNS'
    )

    eb.put_targets(
        Rule=rule_name,
        Targets=[{
            'Id': 'SendToSNS',
            'Arn': sns_topic_arn,
            'InputTransformer': {
                'InputPathsMap': {
                    'alarmName': '$.detail.alarmName',
                    'state': '$.detail.state.value',
                    'reason': '$.detail.state.reason',
                    'region': '$.region',
                    'time': '$.time'
                },
                'InputTemplate': '"[STATUS CHECK ALARM] Alarm: <alarmName> | State: <state> | Region: <region> | Time: <time> | Reason: <reason>"'
            }
        }]
    )
    print(f"[ALARM] Main bus SNS rule ensured in {main_region}")


def subscribe_status_check(instance_id: str, region: str, sns_topic_arn: str) -> Dict[str, Any]:
    """为 EC2 实例创建状态检查 CloudWatch Alarm，通过 EventBridge 跨 region 转发到统一 SNS"""
    import boto3
    cw = boto3.client('cloudwatch', region_name=region)
    alarm_prefix = f"capacity-reservation-status-check-{instance_id}"

    # 解析主 region 和 account
    # sns_topic_arn 格式: arn:aws:sns:{region}:{account}:{name}
    parts = sns_topic_arn.split(':')
    main_region = parts[3]
    main_account = parts[4]
    main_event_bus_arn = f"arn:aws:events:{main_region}:{main_account}:event-bus/default"

    if region == main_region:
        # 同 region：直接使用 SNS
        alarm_action = sns_topic_arn
        print(f"[ALARM] Same region, using SNS directly: {sns_topic_arn}")
    else:
        # 跨 region：CloudWatch Alarm 不配置 SNS Action（让 EventBridge 负责通知）
        # 确保 EventBridge 转发规则已建立
        ensure_eventbridge_forwarding(region, main_account, main_event_bus_arn)
        ensure_main_bus_sns_rule(main_region, sns_topic_arn)
        alarm_action = None
        print(f"[ALARM] Cross-region, using EventBridge forwarding: {region} -> {main_region}")

    alarms = [
        {
            "AlarmName": f"{alarm_prefix}-system",
            "AlarmDescription": f"System status check failed for {instance_id} in {region}",
            "MetricName": "StatusCheckFailed_System",
            "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
        },
        {
            "AlarmName": f"{alarm_prefix}-instance",
            "AlarmDescription": f"Instance status check failed for {instance_id} in {region}",
            "MetricName": "StatusCheckFailed_Instance",
            "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
        },
    ]

    created = []
    for alarm in alarms:
        kwargs = dict(
            AlarmName=alarm["AlarmName"],
            AlarmDescription=alarm["AlarmDescription"],
            ActionsEnabled=True,
            MetricName=alarm["MetricName"],
            Namespace="AWS/EC2",
            Statistic="Maximum",
            Dimensions=alarm["Dimensions"],
            Period=60,
            EvaluationPeriods=2,
            Threshold=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
            TreatMissingData="notBreaching",
        )
        if alarm_action:
            kwargs["AlarmActions"] = [alarm_action]
        cw.put_metric_alarm(**kwargs)
        created.append(alarm["AlarmName"])
        print(f"[ALARM] Created alarm: {alarm['AlarmName']}")

    return {"instanceId": instance_id, "region": region, "alarms": created, "subscribed": True}

def unsubscribe_status_check(instance_id: str, region: str) -> Dict[str, Any]:
    """删除 EC2 实例的状态检查 CloudWatch Alarm"""
    import boto3
    cw = boto3.client('cloudwatch', region_name=region)
    alarm_prefix = f"capacity-reservation-status-check-{instance_id}"
    alarm_names = [f"{alarm_prefix}-system", f"{alarm_prefix}-instance"]

    cw.delete_alarms(AlarmNames=alarm_names)
    print(f"[ALARM] Deleted alarms: {alarm_names}")

    return {"instanceId": instance_id, "region": region, "alarms": alarm_names, "subscribed": False}


def get_status_check_subscription(instance_id: str, region: str) -> Dict[str, Any]:
    """查询 EC2 实例的状态检查订阅状态"""
    import boto3
    cw = boto3.client('cloudwatch', region_name=region)
    alarm_prefix = f"capacity-reservation-status-check-{instance_id}"
    alarm_names = [f"{alarm_prefix}-system", f"{alarm_prefix}-instance"]

    response = cw.describe_alarms(AlarmNames=alarm_names)
    existing = [a["AlarmName"] for a in response.get("MetricAlarms", [])]

    subscribed = len(existing) == 2
    return {
        "instanceId": instance_id,
        "region": region,
        "subscribed": subscribed,
        "alarms": existing,
    }

def lambda_handler(event, context):
    """
    Main Lambda handler for API Gateway requests

    Routes requests based on HTTP method and path:
    - GET /api/capacity-reservations -> get_all_capacity_reservations()
    - GET /api/capacity-reservations/{reservationId}/instances -> get_reservation_instances()

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with CORS headers
    """
    try:
        print(f"收到请求: {json.dumps(event, default=str)}")

        # Extract request information
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}

        # Handle OPTIONS for CORS preflight
        # 解析 instance_id（用于状态检查订阅路由）
        # /api/instances/{instanceId}/subscribe-status-check
        instance_subscribe_path = None
        if '/api/instances/' in path and path.endswith('/subscribe-status-check'):
            # 优先从 pathParameters 取（API Gateway 解析更可靠）
            if path_parameters and path_parameters.get('instanceId'):
                instance_subscribe_path = path_parameters['instanceId']
            else:
                parts = path.split('/')
                if len(parts) >= 4:
                    instance_subscribe_path = parts[3]

        if http_method == 'OPTIONS':
            return format_response(200, {'message': 'OK'})

        # Route GET requests
        if http_method == 'GET':
            # GET /api/capacity-reservations
            if path == '/api/capacity-reservations':
                data = get_all_capacity_reservations()
                return format_response(200, data)

            # GET /api/capacity-reservations/{reservationId}/instances
            elif path.startswith('/api/capacity-reservations/') and path.endswith('/instances'):
                reservation_id = path_parameters.get('reservationId')
                region = query_parameters.get('region')

                if not reservation_id:
                    return format_error_response(
                        400,
                        'MISSING_PARAMETER',
                        'reservationId is required in path'
                    )

                if not region:
                    return format_error_response(
                        400,
                        'MISSING_PARAMETER',
                        'region query parameter is required'
                    )

                data = get_reservation_instances(reservation_id, region)
                return format_response(200, data)

            elif instance_subscribe_path:
                # GET /api/instances/{instanceId}/subscribe-status-check
                qs = event.get('queryStringParameters') or {}
                region = qs.get('region', '')
                if not region:
                    return format_error_response(400, 'MISSING_PARAM', 'region query parameter is required')
                result = get_status_check_subscription(instance_subscribe_path, region)
                return format_response(200, result)

            else:
                return format_error_response(
                    404,
                    'NOT_FOUND',
                    f'Path not found: {path}'
                )

        elif http_method in ('POST', 'DELETE') and instance_subscribe_path:
            instance_id = instance_subscribe_path
            qs = event.get('queryStringParameters') or {}
            region = qs.get('region', '')
            sns_topic_arn = os.environ.get('SNS_TOPIC_ARN', '')

            if not region:
                return format_error_response(400, 'MISSING_PARAM', 'region query parameter is required')
            print(f"[ALARM] {http_method} subscribe-status-check | instance={instance_id} region={region}")

            if http_method == 'POST':
                if not sns_topic_arn:
                    return format_error_response(500, 'CONFIG_ERROR', 'SNS_TOPIC_ARN not configured')
                result = subscribe_status_check(instance_id, region, sns_topic_arn)
                return format_response(200, result)
            else:
                result = unsubscribe_status_check(instance_id, region)
                return format_response(200, result)

        # Method not allowed
        return format_error_response(
            405,
            'METHOD_NOT_ALLOWED',
            f'Method {http_method} not allowed'
        )

    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

        return format_error_response(
            500,
            'INTERNAL_ERROR',
            f'Internal server error: {str(e)}'
        )
