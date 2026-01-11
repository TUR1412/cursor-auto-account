import os
import random
import string
import urllib.parse

from dotenv import load_dotenv
from flask import Flask

import auth
from core.errors import register_error_handlers
from core.logging_config import configure_logging
from core.metrics import register_metrics
from core.middleware import register_request_context
from db_utils import init_db
from models import db
from views.api import api_bp
from views.web import web_bp

# 加载.env文件
load_dotenv()


# 创建并配置 Flask 应用
def create_app():
    configure_logging()
    app = Flask(__name__)

    # 从环境变量获取数据库配置
    app.config["DB_HOST"] = os.getenv("DB_HOST", "localhost")
    app.config["DB_PORT"] = int(os.getenv("DB_PORT", "3306"))
    app.config["DB_USER"] = os.getenv("DB_USER", "root")
    app.config["DB_PASSWORD"] = os.getenv("DB_PASSWORD", "root")
    app.config["DB_NAME"] = os.getenv("DB_NAME", "cursor_accounts")

    # 设置 SQLAlchemy 数据库 URI
    # 优先使用 DATABASE_URL（便于本地/测试环境切换为sqlite）
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
        # 对密码进行URL编码，避免特殊字符（如@）造成解析问题
        encoded_password = urllib.parse.quote_plus(app.config["DB_PASSWORD"])
        app.config["SQLALCHEMY_DATABASE_URI"] = (
            f"mysql+pymysql://{app.config['DB_USER']}:{encoded_password}@{app.config['DB_HOST']}:{app.config['DB_PORT']}/{app.config['DB_NAME']}"
        )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # JWT密钥
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "".join(random.choices(string.ascii_letters + string.digits, k=32))
    )
    # Token有效期（天）
    app.config["TOKEN_EXPIRY_DAYS"] = int(os.getenv("TOKEN_EXPIRY_DAYS", "30"))

    # 初始化数据库
    db.init_app(app)

    # 设置认证模块的密钥和过期时间 - 修复直接设置模块变量
    auth.SECRET_KEY = app.config["SECRET_KEY"]
    auth.TOKEN_EXPIRY_DAYS = app.config["TOKEN_EXPIRY_DAYS"]

    # 注册蓝图
    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)

    # 全局中间件 / 错误处理
    register_request_context(app)
    register_metrics(app)
    register_error_handlers(app)

    return app


# 应用入口
if __name__ == "__main__":
    # 创建应用
    app = create_app()

    # 初始化数据库
    init_db(app)

    # 获取环境变量中的主机和端口，默认为0.0.0.0:8001
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))

    # 启动应用
    app.run(host=host, port=port, debug=(os.getenv("DEBUG", "False").lower() == "true"))
