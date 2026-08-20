# ===== 阶段 1：构建前端（node 环境）=====
FROM node:22-alpine AS build
# 基础镜像：带 Node 22 的精简 Linux（你 package.json 要求 ^22.18.0）
# AS build = 给这个阶段起名叫 build，后面 nginx 阶段从这里取产物

WORKDIR /app
# 容器内工作目录

COPY package.json package-lock.json ./
# 复制依赖清单和锁文件（package-lock.json 锁定精确版本，保证构建可复现）

RUN npm config set registry https://registry.npmmirror.com
# 换国内 npm 镜像源（容器默认官方源，国内下载慢）
# 不加这行 npm install 可能要等很久

RUN npm ci
# 按 package-lock.json 精确安装依赖（npm ci 比 npm install 更快更稳）

COPY . .
# 复制前端全部源码（src、index.html、vite.config.ts 等）
# node_modules 不会进来——.dockerignore 里排除了（前端的 .dockerignore 是 create-vue 自带的）

RUN npm run build
# 执行构建：vue-tsc 类型检查 + vite 打包
# 产物输出到 dist/ 文件夹（静态 HTML + JS + CSS）

# ===== 阶段 2：用 nginx 托管（运行环境）=====
FROM nginx:alpine
# 基础镜像：nginx（轻量 Web 服务器）
# 用新阶段是为了镜像小——node 镜像几百 MB，nginx 才几十 MB

COPY --from=build /app/dist /usr/share/nginx/html
# 从 build 阶段复制构建产物到 nginx 的网页目录
# /usr/share/nginx/html 是 nginx 默认的静态文件根目录

COPY nginx.conf /etc/nginx/conf.d/default.conf
# 复制自定义 nginx 配置，覆盖默认配置
# 默认配置只有静态托管，我们还需要代理 /ask 等到后端

EXPOSE 80
# 容器对外提供 80 端口（nginx 默认端口）

CMD ["nginx", "-g", "daemon off;"]
# 前台启动 nginx（daemon off 保持前台运行，容器才不会退出）
