# OJ Frontend

基于 Vue 3 + TypeScript + Vite 的 Jason227 前端应用。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - JavaScript 的超集
- **Vite** - 下一代前端构建工具
- **Vue Router** - Vue.js 官方路由
- **Pinia** - Vue 官方状态管理库
- **Tailwind CSS** - 功能类优先的 CSS 框架
- **Axios** - HTTP 客户端
- **Monaco Editor** - 代码编辑器

## 项目结构

```
web/
├── src/
│   ├── api/           # API 接口
│   ├── assets/        # 静态资源
│   ├── components/    # 公共组件
│   ├── router/        # 路由配置
│   ├── stores/        # Pinia 状态管理
│   ├── types/         # TypeScript 类型定义
│   ├── utils/         # 工具函数
│   ├── views/         # 页面视图
│   ├── App.vue        # 根组件
│   └── main.ts        # 应用入口
├── public/            # 公共资源
├── .env               # 环境变量
├── index.html         # HTML 模板
├── package.json       # 项目配置
├── tailwind.config.js # Tailwind CSS 配置
└── vite.config.ts     # Vite 配置
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 配置环境变量

复制 `.env.example` 为 `.env` 并配置后端 API 地址：

```bash
cp .env.example .env
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173 查看应用。

### 构建生产版本

```bash
npm run build
```

## 功能模块

- 🔐 **用户认证**：注册、登录、登出
- 📝 **题目管理**：题目列表、题目详情
- 💻 **在线编程**：集成 Monaco Editor 代码编辑器
- 📊 **提交记录**：查看提交历史和评测结果
- 👤 **个人中心**：用户信息管理

## 开发说明

### API 接口

所有 API 请求都通过 `src/api/` 目录中的模块进行。默认 API 地址为 `http://127.0.0.1:8000`，可在 `.env` 文件中修改。

### 状态管理

使用 Pinia 进行状态管理，当前主要状态：
- `authStore`: 用户认证状态

### 路由

路由配置在 `src/router/index.ts` 中，包含路由守卫以保护需要认证的页面。

## 浏览器兼容性

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## License

MIT
