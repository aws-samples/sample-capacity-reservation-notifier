/**
 * InstanceModal Component
 *
 * Modal dialog showing EC2 instances for a Capacity Reservation
 */

import React, { useEffect } from 'react';
import { Modal, Table, Tag, Spin, Alert } from 'antd';
import { useReservationInstances } from '../hooks/useCapacityReservations';
import type { CapacityReservation } from '../types';

interface InstanceModalProps {
  reservation: CapacityReservation | null;
  visible: boolean;
  onClose: () => void;
}

export const InstanceModal: React.FC<InstanceModalProps> = ({ reservation, visible, onClose }) => {
  const { data, isLoading, error, refetch } = useReservationInstances(
    reservation?.CapacityReservationId || '',
    reservation?.Region || '',
    visible && !!reservation
  );

  useEffect(() => {
    if (visible && reservation) {
      refetch();
    }
  }, [visible, reservation, refetch]);

  const columns = [
    {
      title: '实例 ID',
      dataIndex: 'instanceId',
      key: 'instanceId',
      render: (text: string, record: any) => (
        <div>
          <div>{text}</div>
          {record.name && <div style={{ fontSize: 12, color: '#666' }}>{record.name}</div>}
        </div>
      )
    },
    {
      title: '实例类型',
      dataIndex: 'instanceType',
      key: 'instanceType'
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => (
        <Tag color={state === 'running' ? 'green' : 'default'}>
          {state}
        </Tag>
      )
    },
    {
      title: '内网 IP',
      dataIndex: 'privateIpAddress',
      key: 'privateIpAddress'
    },
    {
      title: '公网 IP',
      dataIndex: 'publicIpAddress',
      key: 'publicIpAddress',
      render: (ip: string) => ip || '-'
    },
    {
      title: '可用区',
      dataIndex: 'availabilityZone',
      key: 'availabilityZone'
    }
  ];

  return (
    <Modal
      title={`EC2 实例 - ${reservation?.name || ''}`}
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={null}
    >
      {isLoading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="加载中..." />
        </div>
      )}

      {error && (
        <Alert
          message="加载失败"
          description={error.message}
          type="error"
          showIcon
        />
      )}

      {data && (
        <>
          <div style={{ marginBottom: 16 }}>
            <strong>Region:</strong> {data.region} |
            <strong> Reservation ID:</strong> {data.reservationId}
          </div>
          <div style={{ marginBottom: 16 }}>
            <strong>运行中实例数:</strong> {data.summary.running} / {data.summary.total}
          </div>

          {data.instances.length === 0 ? (
            <Alert
              message="无运行中的实例"
              description="此 Capacity Reservation 当前没有关联的运行中 EC2 实例"
              type="info"
              showIcon
            />
          ) : (
            <Table
              dataSource={data.instances}
              columns={columns}
              rowKey="instanceId"
              pagination={false}
              size="small"
            />
          )}
        </>
      )}
    </Modal>
  );
};
