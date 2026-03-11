"""
Status Calculator Module

Calculate visual status for Capacity Reservations based on their state, dates, and usage.
Based on existing alert logic from handler.py:115-138.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional


def calculate_status(reservation: Dict, now: Optional[datetime] = None) -> str:
    """
    计算 Capacity Reservation 的状态

    Priority order (highest to lowest):
    1. not_fully_launched (红色) - Started but has unused capacity
    2. expiring_soon (黄色) - Expires within 2 days
    3. starting_soon (蓝色) - Starts within 24 hours
    4. normal (绿色) - Everything else

    Args:
        reservation: Capacity Reservation dict from EC2 API
        now: Current UTC datetime (defaults to datetime.now(timezone.utc))

    Returns:
        Status string: 'not_fully_launched' | 'expiring_soon' | 'starting_soon' | 'normal'
    """
    if now is None:
        now = datetime.now(timezone.utc)

    state = reservation.get('State', '').lower()
    start_date = reservation.get('StartDate')
    end_date = reservation.get('EndDate')
    available_count = reservation.get('AvailableInstanceCount', 0)

    # Red: Not fully launched (highest priority)
    # StartDate <= now AND AvailableInstanceCount > 0
    if start_date and start_date <= now and available_count > 0:
        return 'not_fully_launched'

    # Yellow: Expiring soon (2 days)
    # now < EndDate <= now + 2 days AND State = 'active'
    if end_date and state == 'active':
        if now < end_date <= now + timedelta(days=2):
            return 'expiring_soon'

    # Blue: Starting soon (24 hours)
    # now < StartDate <= now + 24 hours
    if start_date:
        if now < start_date <= now + timedelta(hours=24):
            return 'starting_soon'

    # Green: Normal
    return 'normal'


def get_status_color(status: str) -> str:
    """
    Get color code for status

    Args:
        status: Status string

    Returns:
        Hex color code
    """
    color_map = {
        'not_fully_launched': '#ef4444',  # Red
        'expiring_soon': '#facc15',       # Yellow
        'starting_soon': '#3b82f6',       # Blue
        'normal': '#22c55e'               # Green
    }
    return color_map.get(status, '#6b7280')  # Gray as fallback


def calculate_display_message(reservation: Dict, status: str, now: Optional[datetime] = None) -> str:
    """
    Generate human-readable display message for reservation status

    Args:
        reservation: Capacity Reservation dict
        status: Status string from calculate_status()
        now: Current UTC datetime

    Returns:
        Display message string
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if status == 'not_fully_launched':
        available = reservation.get('AvailableInstanceCount', 0)
        total = reservation.get('TotalInstanceCount', 0)
        return f"未启动: {available}/{total} 实例"

    elif status == 'expiring_soon':
        end_date = reservation.get('EndDate')
        if end_date:
            time_left = end_date - now
            days = time_left.days
            hours = time_left.seconds // 3600
            if days > 0:
                return f"到期倒计时: {days}天{hours}小时"
            else:
                return f"到期倒计时: {hours}小时"
        return "即将到期"

    elif status == 'starting_soon':
        start_date = reservation.get('StartDate')
        if start_date:
            time_until = start_date - now
            hours = time_until.seconds // 3600
            minutes = (time_until.seconds % 3600) // 60
            return f"开始倒计时: {hours}小时{minutes}分钟"
        return "即将开始"

    elif status == 'normal':
        return "正常运行"

    return ""


def enrich_reservation_with_status(reservation: Dict, now: Optional[datetime] = None) -> Dict:
    """
    Add status, color, and display info to reservation dict

    Args:
        reservation: Original Capacity Reservation dict
        now: Current UTC datetime

    Returns:
        Enriched reservation dict with additional fields:
        - status: Status string
        - statusColor: Hex color code
        - displayInfo: Dict with message and formatted dates
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Calculate status
    status = calculate_status(reservation, now)

    # Get color
    color = get_status_color(status)

    # Generate display message
    message = calculate_display_message(reservation, status, now)

    # Format dates to Beijing timezone (UTC+8)
    beijing_tz = timezone(timedelta(hours=8))

    display_info = {
        'message': message
    }

    start_date = reservation.get('StartDate')
    if start_date:
        display_info['startDateLocal'] = start_date.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')

    end_date = reservation.get('EndDate')
    if end_date:
        display_info['endDateLocal'] = end_date.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')

    # Get Name tag if exists
    name_tag = None
    for tag in reservation.get('Tags', []):
        if tag.get('Key') == 'Name':
            name_tag = tag.get('Value')
            break

    # Return enriched reservation
    return {
        **reservation,
        'status': status,
        'statusColor': color,
        'displayInfo': display_info,
        'name': name_tag or reservation.get('CapacityReservationId', 'N/A')
    }
