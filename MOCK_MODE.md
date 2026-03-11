# Mock模式使用指南

## 概述

Mock模式允许您在没有真实AWS Capacity Block Reservations的情况下测试Dashboard和邮件通知功能。这对于开发和演示非常有用，避免了创建昂贵的真实资源。

## Mock数据特点

Mock数据包含了各种典型场景：

### 模拟的Regions
- **us-east-1** - 2个CB
- **us-west-2** - 2个CB
- **eu-west-1** - 1个CB
- **ap-northeast-1** - 1个CB

### 模拟的状态类型

| 状态 | 颜色 | Reservation ID | 说明 |
|------|------|----------------|------|
| 🔴 未完全启动 | Red | cr-mock-0123456789abcdef0 | 8个总容量，3个未使用 |
| 🟡 即将到期 | Yellow | cr-mock-1234567890abcdef1 | 1.5天后到期 |
| 🔵 即将开始 | Blue | cr-mock-3456789012abcdef3 | 18小时后开始 |
| 🟢 正常 | Green | cr-mock-2345678901abcdef2 | 正常运行 |

### Mock EC2实例

部分CB包含模拟的运行中EC2实例：
- `cr-mock-0123456789abcdef0`: 5个实例 (p4d.24xlarge)
- `cr-mock-1234567890abcdef1`: 4个实例 (p5.48xlarge)
- `cr-mock-2345678901abcdef2`: 16个实例 (p4de.24xlarge)
- `cr-mock-3456789012abcdef3`: 0个实例 (尚未开始)
- 其他CB也有对应实例

## 启用Mock模式

Mock模式通过环境变量 `ENABLE_MOCK_DATA` 控制。

### 方式1: CDK Stack配置（推荐）

编辑 `capacity_reservation_notifier/capacity_reservation_notifier_stack.py`:

```python
# Notification Lambda
environment={
    "SNS_TOPIC_ARN": topic.topic_arn,
    "ENABLE_MOCK_DATA": "true"  # 启用Mock模式
}

# API Lambda
environment={
    "ENABLE_CORS": "true",
    "ENABLE_MOCK_DATA": "true"  # 启用Mock模式
}
```

**部署更新**：
```bash
cdk deploy
```

### 方式2: AWS Console修改

如果已经部署，可以直接在AWS Console修改：

1. 进入 **Lambda Console**
2. 找到两个函数：
   - `CapacityReservationNotifier` (邮件通知)
   - `CapacityReservationApiHandler` (API)
3. 点击 **Configuration** → **Environment variables**
4. 添加或修改变量：
   - Key: `ENABLE_MOCK_DATA`
   - Value: `true`
5. 点击 **Save**

### 方式3: AWS CLI修改

```bash
# 更新 Notification Lambda
aws lambda update-function-configuration \
  --function-name CapacityReservationNotifierStack-CapacityReservationNotifier-xxx \
  --environment Variables="{SNS_TOPIC_ARN=arn:aws:sns:...,ENABLE_MOCK_DATA=true}"

# 更新 API Lambda
aws lambda update-function-configuration \
  --function-name CapacityReservationNotifierStack-CapacityReservationApiHandler-xxx \
  --environment Variables="{ENABLE_CORS=true,ENABLE_MOCK_DATA=true}"
```

## 测试Mock模式

### 测试邮件通知

手动触发Notification Lambda：

```bash
aws lambda invoke \
  --function-name CapacityReservationNotifierStack-CapacityReservationNotifier-xxx \
  --output json \
  response.json
```

**预期结果**：
- CloudWatch Logs显示 "🎭 Mock模式已启用 - 使用模拟数据生成邮件报告"
- 收到包含6个模拟CB的邮件报告
- 邮件包含各种状态的告警（红/黄/蓝）

### 测试Dashboard API

```bash
# 测试获取所有CB
curl -H "x-api-key: YOUR_API_KEY" \
  "YOUR_API_ENDPOINT/api/capacity-reservations" | jq

# 测试获取实例（使用mock reservation ID）
curl -H "x-api-key: YOUR_API_KEY" \
  "YOUR_API_ENDPOINT/api/capacity-reservations/cr-mock-0123456789abcdef0/instances?region=us-east-1" | jq
```

**预期结果**：
- CloudWatch Logs显示 "🎭 Mock模式已启用"
- API返回4个region的模拟数据
- 不同状态的CB正确显示红/黄/蓝/绿标识
- 点击CB查看实例时显示模拟的EC2实例

### 测试前端Dashboard

1. 确保后端API已启用Mock模式
2. 启动前端：`npm start`
3. 打开 http://localhost:3000

**预期显示**：
- 4个region卡片（us-east-1, us-west-2, eu-west-1, ap-northeast-1）
- 6个Capacity Reservations，各种颜色状态
- 点击CB可查看EC2实例列表（部分有实例，部分无实例）

## 关闭Mock模式

生产环境部署时，务必关闭Mock模式：

```python
# CDK Stack
environment={
    "SNS_TOPIC_ARN": topic.topic_arn,
    "ENABLE_MOCK_DATA": "false"  # 关闭Mock模式
}
```

或删除 `ENABLE_MOCK_DATA` 环境变量（默认为false）。

## Mock数据定制

如果需要修改Mock数据，编辑 `lambda/common/mock_data.py`:

```python
def generate_mock_reservations() -> List[Dict]:
    """修改这里添加或修改Mock CB"""
    mock_data = [
        {
            'CapacityReservationId': 'cr-mock-your-id',
            'Region': 'us-east-1',
            'State': 'active',
            # ... 其他字段
        }
    ]
    return mock_data
```

**重新部署**：
```bash
cdk deploy
```

## 故障排查

### Mock模式未生效

1. **检查环境变量**：
   ```bash
   aws lambda get-function-configuration \
     --function-name CapacityReservationNotifierStack-xxx \
     --query 'Environment.Variables'
   ```

2. **检查CloudWatch Logs**：
   - 查找 "🎭 Mock模式已启用" 日志
   - 如果没有此日志，说明Mock模式未启用

3. **确认部署**：
   ```bash
   cdk diff  # 查看待部署的变更
   cdk deploy  # 重新部署
   ```

### Dashboard显示真实数据

- 确认API Lambda的 `ENABLE_MOCK_DATA` 环境变量为 `true`
- 清除浏览器缓存并刷新Dashboard
- 检查API返回数据（使用curl测试）

## 最佳实践

1. **开发/测试环境**：启用Mock模式
   - 快速迭代开发
   - 演示和截图
   - 不产生AWS费用

2. **生产环境**：关闭Mock模式
   - 使用真实的Capacity Block数据
   - 确保监控准确性

3. **分离环境**：
   - 使用不同的CDK Stack（dev/prod）
   - 通过CDK context或环境变量控制Mock模式

## 参考

- Mock数据文件: [`lambda/common/mock_data.py`](lambda/common/mock_data.py)
- API Handler: [`lambda/api_handler.py`](lambda/api_handler.py)
- Notification Handler: [`lambda/handler.py`](lambda/handler.py)
- CDK Stack: [`capacity_reservation_notifier/capacity_reservation_notifier_stack.py`](capacity_reservation_notifier/capacity_reservation_notifier_stack.py)
