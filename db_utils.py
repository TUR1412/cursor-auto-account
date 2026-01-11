import logging
import os
import re
import time
import urllib.parse

from sqlalchemy import create_engine, text

from models import User, db


# 创建数据库和表
def init_db(app):
    with app.app_context():
        try:
            database_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")

            # 获取数据库配置
            DB_HOST = app.config['DB_HOST']
            DB_PORT = app.config['DB_PORT']
            DB_USER = app.config['DB_USER']
            DB_PASSWORD = app.config['DB_PASSWORD']
            DB_NAME = app.config['DB_NAME']

            # 只有 MySQL 需要预创建 database；sqlite/postgres 等直接 create_all 即可
            if database_uri.startswith("mysql"):
                if not re.fullmatch(r"[A-Za-z0-9_]+", str(DB_NAME)):
                    raise ValueError("DB_NAME 只能包含字母/数字/下划线")

                encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
                engine = create_engine(
                    f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/"
                )
                with engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`"))
                    conn.commit()

            # 创建表
            db.create_all()
            
            logging.info("数据库初始化成功")
            
            # 创建默认管理员账号
            admin_username = os.getenv('ADMIN_USERNAME', 'admin')
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin')
            
            admin = User.query.filter_by(username=admin_username).first()
            if not admin:
                admin = User(
                    username=admin_username,
                    password_hash=User.hash_password(admin_password),
                    created_at=int(time.time())
                )
                db.session.add(admin)
                db.session.commit()
                logging.info(f"创建默认管理员账号: {admin_username}")
            else:
                # update admin password
                admin.password_hash = User.hash_password(admin_password)
                db.session.commit()
                logging.info(f"更新管理员密码: {admin_username}")
                
        except Exception:
            db.session.rollback()
            logging.exception("数据库初始化错误")
            raise
