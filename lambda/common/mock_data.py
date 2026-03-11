"""
Mock Data Generator

Generates realistic mock data for testing Dashboard and email notifications
without creating actual Capacity Block Reservations.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict
import random


def generate_mock_reservations() -> List[Dict]:
    """
    Generate mock Capacity Reservations with various states

    Returns:
        List of mock reservation dictionaries
    """
    now = datetime.now(timezone.utc)

    mock_data = [
        # Region: us-east-1
        {
            'CapacityReservationId': 'cr-mock-0123456789abcdef0',
            'Region': 'us-east-1',
            'State': 'active',
            'InstanceType': 'p4d.24xlarge',
            'AvailabilityZone': 'us-east-1a',
            'TotalInstanceCount': 8,
            'AvailableInstanceCount': 3,  # Not fully launched (RED)
            'StartDate': now - timedelta(hours=2),
            'EndDate': now + timedelta(days=5),
            'Tags': [
                {'Key': 'Name', 'Value': 'ML Training Cluster'},
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'Team', 'Value': 'AI Research'}
            ],
            'InstanceMatchCriteria': 'targeted',
            'CreateDate': now - timedelta(days=10),
            'EphemeralStorage': False,
            'InstancePlatform': 'Linux/UNIX',
            'OwnerId': '123456789012',
            'CapacityReservationArn': 'arn:aws:ec2:us-east-1:123456789012:capacity-reservation/cr-mock-0123456789abcdef0'
        },
        {
            'CapacityReservationId': 'cr-mock-1234567890abcdef1',
            'Region': 'us-east-1',
            'State': 'active',
            'InstanceType': 'p5.48xlarge',
            'AvailabilityZone': 'us-east-1b',
            'TotalInstanceCount': 4,
            'AvailableInstanceCount': 0,  # Fully used
            'StartDate': now - timedelta(hours=12),
            'EndDate': now + timedelta(hours=36),  # Expiring in 1.5 days (YELLOW)
            'Tags': [
                {'Key': 'Name', 'Value': 'Critical GPU Workload'},
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'Priority', 'Value': 'High'}
            ],
            'InstanceMatchCriteria': 'targeted',
            'CreateDate': now - timedelta(days=7),
            'EphemeralStorage': False,
            'InstancePlatform': 'Linux/UNIX',
            'OwnerId': '123456789012',
            'CapacityReservationArn': 'arn:aws:ec2:us-east-1:123456789012:capacity-reservation/cr-mock-1234567890abcdef1'
        },

        # Region: us-west-2
        {
            'CapacityReservationId': 'cr-mock-2345678901abcdef2',
            'Region': 'us-west-2',
            'State': 'active',
            'InstanceType': 'p4de.24xlarge',
            'AvailabilityZone': 'us-west-2a',
            'TotalInstanceCount': 16,
            'AvailableInstanceCount': 0,  # Fully used (GREEN - normal)
            'StartDate': now - timedelta(days=3),
            'EndDate': now + timedelta(days=10),
            'Tags': [
                {'Key': 'Name', 'Value': 'Data Processing Pipeline'},
                {'Key': 'Environment', 'Value': 'Production'}
            ],
            'InstanceMatchCriteria': 'targeted',
            'CreateDate': now - timedelta(days=15),
            'EphemeralStorage': False,
            'InstancePlatform': 'Linux/UNIX',
            'OwnerId': '123456789012',
            'CapacityReservationArn': 'arn:aws:ec2:us-west-2:123456789012:capacity-reservation/cr-mock-2345678901abcdef2'
        },
        {
            'CapacityReservationId': 'cr-mock-3456789012abcdef3',
            'Region': 'us-west-2',
            'State': 'scheduled',
            'InstanceType': 'p5.48xlarge',
            'AvailabilityZone': 'us-west-2c',
            'TotalInstanceCount': 8,
            'AvailableInstanceCount': 8,
            'StartDate': now + timedelta(hours=18),  # Starting in 18 hours (BLUE)
            'EndDate': now + timedelta(days=7),
            'Tags': [
                {'Key': 'Name', 'Value': 'Scheduled Training Job'},
                {'Key': 'Environment', 'Value': 'Staging'},
                {'Key': 'Schedule', 'Value': 'Weekly'}
            ],
            'InstanceMatchCriteria': 'targeted',
            'CreateDate': now - timedelta(days=2),
            'EphemeralStorage': False,
            'InstancePlatform': 'Linux/UNIX',
            'OwnerId': '123456789012',
            'CapacityReservationArn': 'arn:aws:ec2:us-west-2:123456789012:capacity-reservation/cr-mock-3456789012abcdef3'
        },

        # Region: eu-west-1
        {
            'CapacityReservationId': 'cr-mock-4567890123abcdef4',
            'Region': 'eu-west-1',
            'State': 'active',
            'InstanceType': 'p4d.24xlarge',
            'AvailabilityZone': 'eu-west-1a',
            'TotalInstanceCount': 12,
            'AvailableInstanceCount': 5,  # Partially used (RED)
            'StartDate': now - timedelta(hours=6),
            'EndDate': now + timedelta(days=14),
            'Tags': [
                {'Key': 'Name', 'Value': 'EU ML Inference'},
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'Region', 'Value': 'Europe'}
            ],
            'InstanceMatchCriteria': 'targeted',
            'CreateDate': now - timedelta(days=5),
            'EphemeralStorage': False,
            'InstancePlatform': 'Linux/UNIX',
            'OwnerId': '123456789012',
            'CapacityReservationArn': 'arn:aws:ec2:eu-west-1:123456789012:capacity-reservation/cr-mock-4567890123abcdef4'
        },

        # Region: ap-northeast-1
        {
            'CapacityReservationId': 'cr-mock-5678901234abcdef5',
            'Region': 'ap-northeast-1',
            'State': 'active',
            'InstanceType': 'p5.48xlarge',
            'AvailabilityZone': 'ap-northeast-1a',
            'TotalInstanceCount': 6,
            'AvailableInstanceCount': 0,
            'StartDate': now - timedelta(days=1),
            'EndDate': now + timedelta(hours=40),  # Expiring in ~1.7 days (YELLOW)
            'Tags': [
                {'Key': 'Name', 'Value': 'Tokyo AI Training'},
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'CostCenter', 'Value': 'APAC-AI'}
            ],
            'InstanceMatchCriteria': 'targeted',
            'CreateDate': now - timedelta(days=8),
            'EphemeralStorage': False,
            'InstancePlatform': 'Linux/UNIX',
            'OwnerId': '123456789012',
            'CapacityReservationArn': 'arn:aws:ec2:ap-northeast-1:123456789012:capacity-reservation/cr-mock-5678901234abcdef5'
        },
        {
            'CapacityReservationId': 'cr-mock-6789012345abcdef6',
            'Region': 'ap-northeast-1',
            'State': 'expired',
            'InstanceType': 'p4d.24xlarge',
            'AvailabilityZone': 'ap-northeast-1b',
            'TotalInstanceCount': 4,
            'AvailableInstanceCount': 4,
            'StartDate': now - timedelta(days=10),
            'EndDate': now - timedelta(hours=5),  # Expired 5 hours ago (BLACK/DARK GRAY)
            'Tags': [
                {'Key': 'Name', 'Value': 'Expired Test Reservation'},
                {'Key': 'Environment', 'Value': 'Testing'},
                {'Key': 'Status', 'Value': 'Cleanup Required'}
            ],
            'InstanceMatchCriteria': 'targeted',
            'CreateDate': now - timedelta(days=20),
            'EphemeralStorage': False,
            'InstancePlatform': 'Linux/UNIX',
            'OwnerId': '123456789012',
            'CapacityReservationArn': 'arn:aws:ec2:ap-northeast-1:123456789012:capacity-reservation/cr-mock-6789012345abcdef6'
        },
    ]

    return mock_data


def generate_mock_instances(reservation_id: str, region: str) -> List[Dict]:
    """
    Generate mock EC2 instances for a given Capacity Reservation

    Args:
        reservation_id: Capacity Reservation ID
        region: AWS region

    Returns:
        List of mock EC2 instance dictionaries
    """
    # Map of reservation IDs to number of instances
    instance_counts = {
        'cr-mock-0123456789abcdef0': 5,  # 8 total - 3 available = 5 running
        'cr-mock-1234567890abcdef1': 4,  # 4 total - 0 available = 4 running
        'cr-mock-2345678901abcdef2': 16, # 16 total - 0 available = 16 running
        'cr-mock-3456789012abcdef3': 0,  # Not started yet
        'cr-mock-4567890123abcdef4': 7,  # 12 total - 5 available = 7 running
        'cr-mock-5678901234abcdef5': 6,  # 6 total - 0 available = 6 running
        'cr-mock-6789012345abcdef6': 0,  # Expired - no instances
    }

    num_instances = instance_counts.get(reservation_id, 0)

    if num_instances == 0:
        return []

    now = datetime.now(timezone.utc)
    instances = []

    # Get instance type from reservation
    instance_type_map = {
        'cr-mock-0123456789abcdef0': 'p4d.24xlarge',
        'cr-mock-1234567890abcdef1': 'p5.48xlarge',
        'cr-mock-2345678901abcdef2': 'p4de.24xlarge',
        'cr-mock-4567890123abcdef4': 'p4d.24xlarge',
        'cr-mock-5678901234abcdef5': 'p5.48xlarge',
    }

    instance_type = instance_type_map.get(reservation_id, 'p4d.24xlarge')

    for i in range(num_instances):
        instance_id = f'i-mock-{reservation_id[-8:]}{i:02d}'

        instance = {
            'InstanceId': instance_id,
            'InstanceType': instance_type,
            'State': {'Code': 16, 'Name': 'running'},
            'PrivateIpAddress': f'10.0.{random.randint(1, 254)}.{random.randint(1, 254)}',
            'PublicIpAddress': f'54.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}',
            'LaunchTime': now - timedelta(hours=random.randint(1, 72)),
            'Placement': {
                'AvailabilityZone': f'{region}{chr(97 + i % 3)}'  # a, b, c
            },
            'Tags': [
                {'Key': 'Name', 'Value': f'ML-Worker-{i+1:02d}'},
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'CapacityReservationId', 'Value': reservation_id}
            ],
            'CapacityReservationId': reservation_id
        }

        instances.append(instance)

    return instances


def get_mock_regions() -> List[str]:
    """
    Get list of regions with mock data

    Returns:
        List of region names
    """
    return ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-northeast-1']


def get_mock_capacity_reservations(region: str) -> List[Dict]:
    """
    Get mock Capacity Reservations for a specific region

    Args:
        region: AWS region name

    Returns:
        List of mock reservations for the region
    """
    all_reservations = generate_mock_reservations()
    return [r for r in all_reservations if r['Region'] == region]


def get_mock_running_instances_for_reservations(reservations: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Get mock running instances for all reservations

    Args:
        reservations: List of Capacity Reservations

    Returns:
        Dictionary mapping reservation IDs to their instances
    """
    result = {}

    for res in reservations:
        reservation_id = res['CapacityReservationId']
        region = res['Region']
        instances = generate_mock_instances(reservation_id, region)

        if instances:
            result[reservation_id] = instances

    return result
