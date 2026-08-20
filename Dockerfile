FROM python:3.11-slim
# 基础镜像：自带 Python 3.11 的轻量 Linux 系统
# slim = 精简版，体积小；3.11 和你本地版本一致，避免依赖不兼容

WORKDIR /app
# 容器内工作目录：后面所有命令都在 /app 里执行
# 你的代码会复制到 /app，启动时也在 /app 下找 main.py

COPY requirements.txt .
# 先复制依赖清单（单独一步）
# 这样以后改代码重新构建时，依赖安装有缓存，不用重新下载所有包

# 改动前
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 安装依赖（默认官方 PyPI：加速器开启时经代理可达；若改用清华镜像 pypi.tuna 会 SSL 断连报 SSLEOFError）
# RUN = 构建时执行一次，装好的包固化进镜像层

COPY main.py .
# 复制后端入口文件（main.py 在项目根目录）

COPY services ./services
# 复制 services 整个文件夹（rag、agent、database、file_parser 等业务逻辑）

COPY 配置文件 ./配置文件
# 复制配置模块 config.py（注意：config.json 被 .dockerignore 排除了，不进镜像）

COPY knowledge_base ./knowledge_base
# 复制知识库文件（初始宠物店文档 jsonl，容器里建向量库要用）

COPY test.py .
# 复制测试脚本（可选，保持和本地一致）

EXPOSE 8000
# 声明容器对外提供 8000 端口
# 只是"声明"，真正对外映射由 docker-compose 的 ports 决定

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# 容器启动时执行的命令（JSON 数组格式，不能用引号字符串）
# uvicorn main:app = 启动 main.py 里的 app 对象
# --host 0.0.0.0 = 允许外部访问（默认只监听容器内部，必须写这个）
# --port 8000 = 监听端口
