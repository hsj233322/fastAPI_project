# 使用官方轻量的 Python 3.11 镜像
FROM python:3.11-slim

# 禁止生成 pyc 文件，且日志实时输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

# 创建非 root 用户
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# 提前安装 CPU 版 PyTorch
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 创建缓存目录并赋予 appuser 写权限
RUN mkdir -p /app/.cache && chown -R appuser:appgroup /app/.cache

# 复制依赖文件  # 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目所有代码到容器内
COPY --chown=appuser:appgroup . .

# 切换到非 root 用户
USER appuser

# 暴露 FastAPI 的默认端口
EXPOSE 8000

# 启动 FastAPI 应用
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--limit-max-requests", "1000"]