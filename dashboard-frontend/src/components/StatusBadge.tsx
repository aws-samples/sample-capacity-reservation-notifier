/**
 * StatusBadge Component
 *
 * Displays one or multiple colored badges showing reservation status
 */

import React from 'react';
import { Tag, Space } from 'antd';
import type { ReservationStatus } from '../types';

interface StatusTag {
  status: ReservationStatus;
  color: string;
  message?: string;
}

interface StatusBadgeProps {
  // Single status (legacy)
  status?: ReservationStatus;
  message?: string;
  // Multiple statuses (new)
  statusTags?: StatusTag[];
}

const statusTextMap: Record<ReservationStatus, string> = {
  expired: '已过期',
  not_fully_launched: '未完全启动',
  expiring_soon: '即将到期',
  starting_soon: '即将开始',
  normal: '正常'
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, message, statusTags }) => {
  // Use statusTags if provided (new multi-status mode)
  if (statusTags && statusTags.length > 0) {
    return (
      <Space size={4} wrap>
        {statusTags.map((tag, idx) => (
          <Tag
            key={idx}
            color={tag.color}
            style={{ fontSize: '13px', padding: '2px 10px', margin: 0 }}
          >
            {statusTextMap[tag.status] || tag.status}
            {tag.message && tag.status !== 'normal' && ` - ${tag.message}`}
          </Tag>
        ))}
      </Space>
    );
  }

  // Legacy single status
  if (status) {
    const color = {
      expired: '#4b5563',
      not_fully_launched: '#ef4444',
      expiring_soon: '#facc15',
      starting_soon: '#3b82f6',
      normal: '#22c55e'
    }[status] || '#6b7280';

    return (
      <Tag color={color} style={{ fontSize: '14px', padding: '4px 12px' }}>
        {statusTextMap[status]}
        {message && ` - ${message}`}
      </Tag>
    );
  }

  return null;
};
