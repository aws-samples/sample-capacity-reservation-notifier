# Capacity Reservation Dashboard

实时Web Dashboard，用于监控AWS Capacity Block预留状态。

## 功能特性

- 📊 实时查看所有AWS region的Capacity Reservations
- 🎨 根据状态显示不同颜色标识：
  - 🔴 红色：未完全启动
  - 🟡 黄色：即将到期（2天内）
  - 🔵 蓝色：即将开始（24小时内）
  - 🟢 绿色：正常运行
- 🖱️ 点击CB查看关联的运行中EC2实例
- 🔄 自动刷新（每5分钟）
- 📱 响应式设计

## 前置要求

- Node.js 16+
- npm or yarn

## 安装

```bash
# 安装依赖
npm install
```

## 配置

1. 复制环境变量模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入API配置：
```
REACT_APP_API_ENDPOINT=https://your-api-id.execute-api.region.amazonaws.com/prod
REACT_APP_API_KEY=your-api-key-here
```

获取API Endpoint和Key：
- API Endpoint: 从CDK部署输出中获取 `ApiEndpoint`
- API Key: AWS Console -> API Gateway -> API Keys

## 本地开发

```bash
npm start
```

访问 http://localhost:3000

## 构建生产版本

```bash
npm run build
```

构建产物在 `build/` 目录。

## AWS Amplify 部署

1. 配置环境变量（构建前必须配置）：
```bash
cp .env.example .env
# 编辑 .env 文件，填入API Endpoint和API Key
```

2. 构建生产版本：
```bash
npm run build
```

3. 压缩构建文件：
```bash
cd build
zip -r ../dashboard.zip .
cd ..
```

4. 登录 [AWS Amplify Console](https://console.aws.amazon.com/amplify/)

5. 点击 **Get Started** → **Amplify Hosting** → **Deploy without Git provider**

6. 应用名称: `capacity-reservation-dashboard`，环境: `production`

7. 上传 `dashboard.zip` 文件

8. 点击 **Save and deploy**

**参考**: [AWS Amplify Manual Deploys](https://docs.aws.amazon.com/amplify/latest/userguide/manual-deploys.html)

9. 强烈建议开启 Hosting --> Access Control，设置访问用户名密码

## 目录结构

```
src/
├── components/          # React组件
│   ├── Dashboard.tsx   # 主Dashboard
│   ├── RegionCard.tsx  # Region分组卡片
│   ├── ReservationCard.tsx  # CB卡片
│   ├── InstanceModal.tsx    # EC2实例Modal
│   └── StatusBadge.tsx      # 状态徽章
├── hooks/              # 自定义Hooks
│   └── useCapacityReservations.ts
├── services/           # API服务
│   └── api.ts
├── types/              # TypeScript类型定义
│   └── index.ts
├── App.tsx             # 根组件
└── index.tsx           # 入口文件
```

## 技术栈

- React 18
- TypeScript
- Ant Design (UI组件库)
- React Query (数据获取和缓存)
- Axios (HTTP客户端)

## 故障排除

### API调用失败

1. 检查 `.env` 文件配置是否正确
2. 验证API Key是否有效
3. 确认API Gateway CORS配置
4. 查看浏览器Console错误信息

### 页面空白

1. 检查浏览器Console是否有错误
2. 确认后端API是否正常运行
3. 尝试清除浏览器缓存

## License

MIT-0
