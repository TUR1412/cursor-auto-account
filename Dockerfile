FROM python:3.9-slim

WORKDIR /app

# 复制项目文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建模板目录和截图目录
RUN mkdir -p templates screenshots

# 暴露端口
EXPOSE 8001

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8001
ENV DEBUG=false

# 创建启动脚本
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Container healthcheck (does not require curl/wget)
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 CMD python -c "import urllib.request, sys; u=urllib.request.urlopen('http://127.0.0.1:8001/api/health', timeout=2); sys.exit(0 if getattr(u,'status',200)==200 else 1)"

# 启动服务
CMD ["/start.sh"]
