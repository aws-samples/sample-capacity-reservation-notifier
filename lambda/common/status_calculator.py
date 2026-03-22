"""
Status Calculator Module

Calculate visual status for Capacity Reservations based on their state, dates, and usage.
Supports multiple concurrent statuses for a single reservation.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List


def calculate_statuses(reservation: Dict, now: Optional[datetime] = None) -> List[str]:
    """
    计算 Capacity Reservation 的所有适用状态（支持多个并发状态）

    Returns list of applicable statuses (may be multiple):
    - 'expired'            黑色/深灰色 - 已过期
    - 'not_fully_launched' 红色       - 已开始但未满开机
    - 'expiring_soon'      黄色       - 2天内到期
    - 'starting_soon'      蓝色       - 24小时内开始
    - 'normal'             绿色       - 正常

    Priority: expired is exclusive (if expired, return only expired)
    All other statuses can coexist.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    state = reservation.get('State', '').lower()
    start_date = reservation.get('StartDate')
    end_date = reservation.get('EndDate')
    available_count = reservation.get('AvailableInstanceCount', 0)

    # Expired is exclusive - highest priority, return immediately
    if end_date and end_date < now:
        return ['expired']

    statuses = []

    # Not fully launched: started but has unused capacity
    if start_date and start_date <= now and available_count > 0:
        statuses.append('not_fully_launched')

    # Expiring soon: within 2 days (applies to both active and scheduled)
    if end_date and now < end_date <= now + timedelta(days=2):
        statuses.append('expiring_soon')

    # Starting soon: within 24 hours
    if start_date and now < start_date <= now + timedelta(hours=24):
        statuses.append('starting_soon')

    # Normal if no alerts
    if not statuses:
        statuses.append('normal')

    return statuses


def calculate_status(reservation: Dict, now: Optional[datetime] = None) -> str:
    """
    Legacy single-status API (returns highest priority status).
    Kept for backward compatibility.
    """
    statuses = calculate_statuses(reservation, now)
    return statuses[0]


def get_status_color(status: str) -> str:
    color_map = {
        'expired': '#4b5563',
        'not_fully_launched': '#ef4444',
        'expiring_soon': '#facc15',
        'starting_soon': '#3b82f6',
        'normal': '#22c55e'
    }
    return color_map.get(status, '#6b7280')


def calculate_display_message(reservation: Dict, status: str, now: Optional[datetime] = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)

    if status == 'expired':
        end_date = reservation.get('EndDate')
        if end_date:
            time_passed = now - end_date
            days = time_passed.days
            if days > 0:
                return f"已过期 {days} 天"
            else:
                hours = time_passed.seconds // 3600
                return f"已过期 {hours} 小时"
        return "已过期"

    elif status == 'not_fully_launched':
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
    if now is None:
        now = datetime.now(timezone.utc)

    # Calculate all applicable statuses
    statuses = calculate_statuses(reservation, now)
    primary_status = statuses[0]

    # Build status tags list for frontend
    status_tags = []
    for s in statuses:
        status_tags.append({
            'status': s,
            'color': get_status_color(s),
            'message': calculate_display_message(reservation, s, now)
        })

    # Legacy single status fields (backward compatibility)
    color = get_status_color(primary_status)
    message = calculate_display_message(reservation, primary_status, now)

    # Format dates to Beijing timezone (UTC+8)
    beijing_tz = timezone(timedelta(hours=8))
    display_info = {'message': message}

    start_date = reservation.get('StartDate')
    if start_date:
        display_info['startDateLocal'] = start_date.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')

    end_date = reservation.get('EndDate')
    if end_date:
        display_info['endDateLocal'] = end_date.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M:%S CST')

    name_tag = None
    for tag in reservation.get('Tags', []):
        if tag.get('Key') == 'Name':
            name_tag = tag.get('Value')
            break

    return {
        **reservation,
        'status': primary_status,       # legacy: highest priority
        'statuses': statuses,           # new: all applicable statuses
        'statusTags': status_tags,      # new: full tag list with colors/messages
        'statusColor': color,
        'displayInfo': display_info,
        'name': name_tag or reservation.get('CapacityReservationId', 'N/A')
    }
