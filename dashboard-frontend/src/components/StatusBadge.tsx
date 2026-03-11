/**
 * StatusBadge Component
 *
 * Displays a colored badge showing the reservation status
 */

import React from 'react';
import { Tag } from 'antd';
import type { ReservationStatus } from '../types';

interface StatusBadgeProps {
  status: ReservationStatus;
  message?: string;
}

const statusConfig: Record<ReservationStatus, { color: string; text: string }> = {
  expired: {
    color: '#4b5563',
    text: '已过期'
  },
  not_fully_launched: {
    color: '#ef4444',
    text: '未完全启动'
  },
  expiring_soon: {
    color: '#facc15',
    text: '即将到期'
  },
  starting_soon: {
    color: '#3b82f6',
    text: '即将开始'
  },
  normal: {
    color: '#22c55e',
    text: '正常'
  }
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, message }) => {
  const config = statusConfig[status];

  return (
    <Tag color={config.color} style={{ fontSize: '14px', padding: '4px 12px' }}>
      {config.text}
      {message && ` - ${message}`}
    </Tag>
  );
};
