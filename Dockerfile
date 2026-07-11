# 使用官方轻量的 Python 3.11 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（如果你用到了 mysqlclient 等需要编译的库，需要加 gcc，这里用 pymysql 就不需要）
# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目所有代码到容器内
COPY . .

# 暴露 FastAPI 的默认端口
EXPOSE 8000

# 启动命令（使用 uvicorn 启动，0.0.0.0 允许外部访问）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]