/**
 * RegionCard Component
 *
 * Displays all Capacity Reservations for a specific region
 */

import React, { useState } from 'react';
import { Card, Space, Tag, Statistic, Row, Col, Collapse } from 'antd';
import { GlobalOutlined, DatabaseOutlined } from '@ant-design/icons';
import type { RegionData, CapacityReservation } from '../types';
import { ReservationCard } from './ReservationCard';
import { InstanceModal } from './InstanceModal';

interface RegionCardProps {
  regionData: RegionData;
}

export const RegionCard: React.FC<RegionCardProps> = ({ regionData }) => {
  const [selectedReservation, setSelectedReservation] = useState<CapacityReservation | null>(null);
  const [modalVisible, setModalVisible] = useState(false);

  const handleReservationClick = (reservation: CapacityReservation) => {
    setSelectedReservation(reservation);
    setModalVisible(true);
  };

  const handleModalClose = () => {
    setModalVisible(false);
  };

  const { regionName, reservations, summary } = regionData;

  return (
    <>
      <Card
        style={{ marginBottom: 24 }}
        title={
          <Space>
            <GlobalOutlined />
            <span>{regionName}</span>
            <Tag color="blue">{summary.total} 个预留</Tag>
          </Space>
        }
      >
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Statistic
              title="总计"
              value={summary.total}
              prefix={<DatabaseOutlined />}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="已过期"
              value={summary.expired}
              valueStyle={{ color: '#4b5563' }}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="未完全启动"
              value={summary.not_fully_launched}
              valueStyle={{ color: '#ef4444' }}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="即将到期"
              value={summary.expiring_soon}
              valueStyle={{ color: '#facc15' }}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="即将开始"
              value={summary.starting_soon}
              valueStyle={{ color: '#3b82f6' }}
            />
          </Col>
          <Col span={4}>
            <Statistic
              title="正常"
              value={summary.normal}
              valueStyle={{ color: '#22c55e' }}
            />
          </Col>
        </Row>

        <Collapse
          defaultActiveKey={summary.expiring_soon > 0 || summary.not_fully_launched > 0 ? ['1'] : []}
          items={[{
            key: '1',
            label: `查看所有预留 (${reservations.length})`,
            children: (
              <Space direction="vertical" style={{ width: '100%' }}>
                {reservations.map((reservation) => (
                  <ReservationCard
                    key={reservation.CapacityReservationId}
                    reservation={reservation}
                    onClick={() => handleReservationClick(reservation)}
                  />
                ))}
              </Space>
            )
          }]}
        />
      </Card>

      <InstanceModal
        reservation={selectedReservation}
        visible={modalVisible}
        onClose={handleModalClose}
      />
    </>
  );
};
