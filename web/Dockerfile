# 前端多阶段构建：Node 构建 -> nginx 托管
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
# 使用国内 npm 镜像源，避免服务器直连国外 registry 下载缓慢/不完整
RUN npm ci --registry=https://registry.npmmirror.com

COPY . .
# 生产构建（读 .env.production；VITE_API_BASE_URL 留空走同域相对路径）
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
