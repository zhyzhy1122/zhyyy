FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 先复制依赖清单单独一层：改代码时依赖层可复用缓存，不用重装
COPY requirements.txt .

# 默认走官方 PyPI（容器内代理只用于访问被墙站点，PyPI 走直连）
# 国内网络如需换镜像源：
#   docker compose build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir -r requirements.txt -i ${PIP_INDEX_URL}

# 后端入口 + 检索评测脚本
COPY main.py run_retrieval_eval.py ./
# 业务逻辑
COPY services ./services
# 配置目录（config.json 被 .dockerignore 排除，运行时由数据卷挂载注入，密钥不进镜像）
COPY config ./config
# 初始知识库（首次建库需要）
COPY knowledge_base ./knowledge_base
# 运维自检脚本（docker exec pet_shop_backend python scripts/smoke_redis.py）
COPY scripts ./scripts

EXPOSE 8000

# 健康检查：容器编排时可直接判断服务是否就绪
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3).status==200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
