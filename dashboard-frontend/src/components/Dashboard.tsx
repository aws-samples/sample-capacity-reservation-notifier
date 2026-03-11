/**
 * Dashboard Component
 *
 * Main dashboard container showing all regions and reservations
 */

import React from 'react';
import { Layout, Space, Statistic, Card, Row, Col, Spin, Alert, Button } from 'antd';
import { ReloadOutlined, CloudOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useCapacityReservations } from '../hooks/useCapacityReservations';
import { RegionCard } from './RegionCard';

const { Header, Content } = Layout;

export const Dashboard: React.FC = () => {
  const { data, isLoading, error, refetch } = useCapacityReservations();

  if (isLoading) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ background: '#001529', color: '#fff', padding: '0 24px' }}>
          <h1 style={{ color: '#fff', margin: 0 }}>Capacity Reservation Dashboard</h1>
        </Header>
        <Content style={{ padding: '24px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <Spin size="large" tip="加载数据中..." />
        </Content>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ background: '#001529', color: '#fff', padding: '0 24px' }}>
          <h1 style={{ color: '#fff', margin: 0 }}>Capacity Reservation Dashboard</h1>
        </Header>
        <Content style={{ padding: '24px' }}>
          <Alert
            message="加载失败"
            description={error.message}
            type="error"
            showIcon
            action={
              <Button size="small" danger onClick={() => refetch()}>
                重试
              </Button>
            }
          />
        </Content>
      </Layout>
    );
  }

  const summary = data?.summary;
  const regions = data?.regions || [];

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Header style={{ background: '#001529', color: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ color: '#fff', margin: 0 }}>Capacity Reservation Dashboard</h1>
        <div>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
            style={{ marginRight: 16 }}
          >
            刷新
          </Button>
          <span style={{ color: '#8c8c8c' }}>
            更新时间: {data?.timestampLocal}
          </span>
        </div>
      </Header>

      <Content style={{ padding: '24px' }}>
        {summary && (
          <Card style={{ marginBottom: 24 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="总计 Regions"
                  value={summary.totalRegions}
                  prefix={<CloudOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="总计预留"
                  value={summary.totalReservations}
                  prefix={<DatabaseOutlined />}
                />
              </Col>
              <Col span={3}>
                <Statistic
                  title="未完全启动"
                  value={summary.byStatus.not_fully_launched}
                  valueStyle={{ color: '#ef4444' }}
                />
              </Col>
              <Col span={3}>
                <Statistic
                  title="即将到期"
                  value={summary.byStatus.expiring_soon}
                  valueStyle={{ color: '#facc15' }}
                />
              </Col>
              <Col span={3}>
                <Statistic
                  title="即将开始"
                  value={summary.byStatus.starting_soon}
                  valueStyle={{ color: '#3b82f6' }}
                />
              </Col>
              <Col span={3}>
                <Statistic
                  title="正常"
                  value={summary.byStatus.normal}
                  valueStyle={{ color: '#22c55e' }}
                />
              </Col>
            </Row>
          </Card>
        )}

        <Space direction="vertical" style={{ width: '100%' }}>
          {regions.length === 0 ? (
            <Alert
              message="没有找到 Capacity Reservations"
              description="当前没有任何活动的 Capacity Reservations"
              type="info"
              showIcon
            />
          ) : (
            regions.map((regionData) => (
              <RegionCard key={regionData.regionName} regionData={regionData} />
            ))
          )}
        </Space>
      </Content>
    </Layout>
  );
};
