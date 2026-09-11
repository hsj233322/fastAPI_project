FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# 非 root 用户
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# CPU 版 torch（bge 只需要 CPU 推理就够）
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 项目代码
COPY --chown=appuser:appgroup . .

# 运行时需要可写的目录（放 COPY 之后，避免被覆盖权限）
RUN mkdir -p /app/.cache /app/logs \
    && chown -R appuser:appgroup /app/.cache /app/logs

USER appuser
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]