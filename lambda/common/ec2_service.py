"""
EC2 Service Module

Shared functions for querying AWS EC2 Capacity Reservations and Instances.
Extracted from handler.py for reuse across notification and API Lambdas.
"""

import boto3
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed


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


def get_instances_by_reservation_id(reservation_id: str, region: str) -> List[Dict]:
    """
    查询特定 Capacity Reservation 关联的运行中 EC2 实例

    Args:
        reservation_id: Capacity Reservation ID
        region: AWS region name

    Returns:
        List of instance dictionaries
    """
    ec2 = boto3.client('ec2', region_name=region)

    try:
        instances = []
        paginator = ec2.get_paginator('describe_instances')

        for page in paginator.paginate(
            Filters=[
                {'Name': 'capacity-reservation-id', 'Values': [reservation_id]},
                {'Name': 'instance-state-name', 'Values': ['running']},
            ]
        ):
            for reservation in page['Reservations']:
                for inst in reservation['Instances']:
                    instances.append(inst)

        return instances

    except Exception as e:
        print(f"查询 reservation {reservation_id} 的实例时出错: {str(e)}")
        return []


def query_all_reservations_parallel(regions: List[str] = None, max_workers: int = 10) -> List[Dict]:
    """
    并行查询所有 region 的 Capacity Reservations（性能优化版本）

    Args:
        regions: List of region names (if None, queries all available regions)
        max_workers: Maximum number of concurrent threads

    Returns:
        Combined list of all reservations across regions
    """
    if regions is None:
        regions = get_all_regions()

    all_reservations = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_region = {
            executor.submit(get_capacity_reservations, region): region
            for region in regions
        }

        for future in as_completed(future_to_region):
            region = future_to_region[future]
            try:
                reservations = future.result()
                if reservations:
                    all_reservations.extend(reservations)
                    print(f"Region {region}: 找到 {len(reservations)} 个 CB")
            except Exception as e:
                print(f"并行查询 region {region} 失败: {str(e)}")

    return all_reservations
