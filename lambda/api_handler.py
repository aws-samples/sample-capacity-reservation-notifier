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
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
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
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
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
            status = res['status']
            region_summary[status] += 1
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

            else:
                return format_error_response(
                    404,
                    'NOT_FOUND',
                    f'Path not found: {path}'
                )

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
