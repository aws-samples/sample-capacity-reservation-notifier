[English](README_EN.md) | 中文

# Capacity Reservation Notifier

本项目基于AWS Serverless架构，实现跨区域Capacity Blocks到期提前预警、未开机 CB 闲置监控，助力客户避免业务中断与成本浪费。

## 解决方案与核心功能

本项目采用无服务器架构，实现全自动化部署与运行，核心能力包括：

- 跨区域自动化扫描

系统每日多次批量扫描客户账号下所有 Region 的 Capacity Blocks 资源，自动汇总预订信息、到期时间、使用状态，形成统一资源视图。

- 到期主动预警推送

按预设周期生成 CB 到期报表，通过邮件自动推送告警信息，让客户提前规划业务停机与资源迁移，避免因回收预警过晚导致业务影响。

- CB-EC2 实例自动关联

提供专用映射脚本，自动建立 CB 预订与对应 EC2 实例的关联关系，精准识别需重点保障与迁移的目标实例，简化资产处置流程。

- 未开机 CB 专项监控

新增对已计费但未启动 EC2 的 CB 资源监控能力，及时识别闲置资源并告警，提醒客户开机或调整资源策略，杜绝无效成本损耗。




## 项目背景
AWS Capacity Blocks（CB）为客户提供专属算力预订能力，但原生机制存在明显使用短板：默认仅在实例回收前 30 分钟发出告警，预留时间过短，客户无法完成业务停机、服务切换、数据迁移等标准化流程，极易引发业务中断与资产风险。

同时客户在日常运维中面临三大核心痛点：

- 人工成本高：需跨多个 Region 手动核查预订到期情况，操作繁琐、效率低下；

- 资源关联难：无法将 CB 预订与对应 EC2 实例直接映射，到期前迁移工作难以推进；

- 成本易浪费：已计费的 CB 资源常因 EC2 实例未及时开机而闲置，造成不必要费用支出。



## 效果

![preview.png](resources/preview.png)

- 每天北京时间 08:00 和 18:00 自动扫描所有 AWS regions 的 active Capacity Reservations
- 通过 SNS 发送邮件通知
- 所有日志记录到 CloudWatch Logs


## 架构

![architecture.png](resources/architecture.png)


- **EventBridge Scheduler**: 定时触发（每天 2 次）
- **Lambda Function**: 扫描 Capacity Reservations 并发送通知
- **SNS Topic**: 邮件通知
- **CloudWatch Logs**: 日志记录（保留 30 天）

## 前置要求

- Python 3.11+
- AWS CLI 已配置
- AWS CDK 已安装：`npm install -g aws-cdk`
- 虚拟环境工具


## 部署

请使用CloudShell进行部署


1. Bootstrap CDK（首次部署）：
```bash
cd capacity-reservation-notifier

pip install -r requirements.txt

cdk bootstrap
```

2. 合成 CloudFormation 模板：
```bash
cdk synth
```

3. 部署 Stack：
```bash
cdk deploy
```

4. 记录输出的 SNS Topic ARN

5. 创建 SNS 邮件订阅：

- 通过脚本进行订阅

```bash
aws sns subscribe \
  --topic-arn <SNS_TOPIC_ARN> \
  --protocol email \
  --notification-endpoint <YOUR_EMAIL>
```
- 在SNS页面进行收到配置


6. 确认邮件订阅（检查邮箱并点击确认链接）



## 测试-手动触发

手动触发 Lambda 函数进行测试：

```bash
aws lambda invoke \
  --function-name CapacityReservationNotifierStack-CapacityReservationNotifier \
  --output json \
  response.json
```

## 成本

预计月度成本约 $0.03（几乎全部在 AWS 免费套餐内）

## 许可证

MIT-0, 请看 LICENSE 文件。

## Security

更多信息，请看 [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications).

