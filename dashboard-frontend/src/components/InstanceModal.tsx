/**
 * InstanceModal Component
 *
 * Modal dialog showing EC2 instances for a Capacity Reservation
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Modal, Table, Tag, Spin, Alert, Button, Tooltip, message } from 'antd';
import { BellOutlined, BellFilled, LoadingOutlined } from '@ant-design/icons';
import { useReservationInstances } from '../hooks/useCapacityReservations';
import { api } from '../services/api';
import type { CapacityReservation, Instance } from '../types';

interface InstanceModalProps {
  reservation: CapacityReservation | null;
  visible: boolean;
  onClose: () => void;
}

interface SubscriptionState {
  subscribed: boolean;
  loading: boolean;
}

export const InstanceModal: React.FC<InstanceModalProps> = ({ reservation, visible, onClose }) => {
  const { data, isLoading, error, refetch } = useReservationInstances(
    reservation?.CapacityReservationId || '',
    reservation?.Region || '',
    visible && !!reservation
  );

  const [subscriptions, setSubscriptions] = useState<Record<string, SubscriptionState>>({});

  useEffect(() => {
    if (visible && reservation) {
      refetch();
    }
  }, [visible, reservation, refetch]);

  useEffect(() => {
    if (!data?.instances || !reservation?.Region) return;
    const region = reservation.Region;

    data.instances.forEach(async (instance: Instance) => {
      setSubscriptions(prev => ({
        ...prev,
        [instance.instanceId]: { subscribed: false, loading: true }
      }));
      try {
        const result = await api.getStatusCheckSubscription(instance.instanceId, region);
        setSubscriptions(prev => ({
          ...prev,
          [instance.instanceId]: { subscribed: result.subscribed, loading: false }
        }));
      } catch {
        setSubscriptions(prev => ({
          ...prev,
          [instance.instanceId]: { subscribed: false, loading: false }
        }));
      }
    });
  }, [data?.instances, reservation?.Region]);

  const handleToggleSubscription = useCallback(async (instanceId: string) => {
    const region = reservation?.Region;
    if (!region) return;

    const current = subscriptions[instanceId];
    const isSubscribed = current?.subscribed;

    setSubscriptions(prev => ({
      ...prev,
      [instanceId]: { ...prev[instanceId], loading: true }
    }));

    try {
      if (isSubscribed) {
        await api.unsubscribeStatusCheck(instanceId, region);
        message.success(`已取消 ${instanceId} 的状态检查告警`);
        setSubscriptions(prev => ({
          ...prev,
          [instanceId]: { subscribed: false, loading: false }
        }));
      } else {
        await api.subscribeStatusCheck(instanceId, region);
        message.success(`已为 ${instanceId} 订阅状态检查告警`);
        setSubscriptions(prev => ({
          ...prev,
          [instanceId]: { subscribed: true, loading: false }
        }));
      }
    } catch (err: any) {
      message.error(`操作失败: ${err.message}`);
      setSubscriptions(prev => ({
        ...prev,
        [instanceId]: { ...prev[instanceId], loading: false }
      }));
    }
  }, [reservation?.Region, subscriptions]);

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
    },
    {
      title: '状态检查告警',
      key: 'statusCheckAlarm',
      width: 140,
      render: (_: any, record: Instance) => {
        const state = subscriptions[record.instanceId];
        const loading = state?.loading;
        const isSubscribed = state?.subscribed;

        return (
          <Tooltip title={isSubscribed
            ? '已订阅状态检查告警，点击取消'
            : '订阅状态检查告警（系统/实例状态检查失败时发送邮件）'
          }>
            <Button
              size="small"
              type={isSubscribed ? 'primary' : 'default'}
              icon={loading
                ? <LoadingOutlined />
                : isSubscribed ? <BellFilled /> : <BellOutlined />
              }
              onClick={() => handleToggleSubscription(record.instanceId)}
              disabled={loading}
            >
              {isSubscribed ? '已订阅' : '订阅告警'}
            </Button>
          </Tooltip>
        );
      }
    }
  ];

  return (
    <Modal
      title={`EC2 实例 - ${reservation?.name || ''}`}
      open={visible}
      onCancel={onClose}
      width={1100}
      footer={null}
    >
      {isLoading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="加载中..." />
        </div>
      )}

      {error && (
        <Alert message="加载失败" description={error.message} type="error" showIcon />
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
          <Alert
            message="状态检查告警"
            description="点击「订阅告警」后，当该 EC2 实例的系统状态检查或实例状态检查失败时，将通过 SNS 发送邮件告警。"
            type="info"
            showIcon
            closable
            style={{ marginBottom: 16 }}
          />
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
