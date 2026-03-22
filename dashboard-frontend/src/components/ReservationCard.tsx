/**
 * ReservationCard Component
 *
 * Displays a single Capacity Reservation with its details
 */

import React from 'react';
import { Card, Descriptions, Space } from 'antd';
import { ClockCircleOutlined, DatabaseOutlined } from '@ant-design/icons';
import type { CapacityReservation } from '../types';
import { StatusBadge } from './StatusBadge';

interface ReservationCardProps {
  reservation: CapacityReservation;
  onClick: () => void;
}

export const ReservationCard: React.FC<ReservationCardProps> = ({ reservation, onClick }) => {
  const {
    name,
    status,
    statusTags,
    statusColor,
    displayInfo,
    State,
    InstanceType,
    AvailabilityZone,
    TotalInstanceCount,
    AvailableInstanceCount
  } = reservation;

  return (
    <Card
      hoverable
      onClick={onClick}
      style={{
        marginBottom: 16,
        borderLeft: `4px solid ${statusColor}`,
        cursor: 'pointer'
      }}
      bodyStyle={{ padding: 16 }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <strong style={{ fontSize: 16 }}>{name}</strong>
          <StatusBadge statusTags={statusTags} status={status} message={displayInfo.message} />
        </div>

        <Descriptions size="small" column={2}>
          <Descriptions.Item label="状态">
            {State}
          </Descriptions.Item>
          <Descriptions.Item label="实例类型">
            <DatabaseOutlined /> {InstanceType}
          </Descriptions.Item>
          <Descriptions.Item label="可用区">
            {AvailabilityZone}
          </Descriptions.Item>
          <Descriptions.Item label="容量">
            {TotalInstanceCount - AvailableInstanceCount} / {TotalInstanceCount} 使用中
          </Descriptions.Item>
        </Descriptions>

        {displayInfo.startDateLocal && (
          <div style={{ fontSize: 12, color: '#666' }}>
            <ClockCircleOutlined /> 开始: {displayInfo.startDateLocal}
          </div>
        )}
        {displayInfo.endDateLocal && (
          <div style={{ fontSize: 12, color: '#666' }}>
            <ClockCircleOutlined /> 结束: {displayInfo.endDateLocal}
          </div>
        )}
      </Space>
    </Card>
  );
};
