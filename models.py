from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

# 用户模型
class User(db.Model):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    last_login = Column(BigInteger, nullable=True)
    domain = Column(String(255), default='zoowayss.top')
    temp_email_address = Column(String(255), default='zoowayss@mailto.plus',nullable=True)

    # 关联用户的账号
    accounts = relationship("Account", back_populates="user")

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'domain': self.domain,
            'temp_email_address': self.temp_email_address
        }

    @staticmethod
    def hash_password(password):
        # 使用Werkzeug提供的安全哈希（兼容Flask生态）
        return generate_password_hash(password)

    @staticmethod
    def _legacy_hash_password(password: str) -> str:
        import hashlib

        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password):
        # 兼容旧数据：历史版本使用sha256明文哈希
        if self.password_hash and ("$" in self.password_hash or ":" in self.password_hash):
            return check_password_hash(self.password_hash, password)
        return self.password_hash == User._legacy_hash_password(password)

    @property
    def is_admin(self) -> bool:
        # 兼容项目当前实现：简单地以ID=1作为管理员
        return self.id == 1

# 定义账号模型
class Account(db.Model):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    create_time = Column(BigInteger, nullable=False)
    expire_time = Column(BigInteger, nullable=False)
    is_used = Column(Integer, default=0)  # 0: 未使用, 1: 已使用
    is_deleted = Column(Integer, default=0)  # 0: 未删除, 1: 已删除
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # 关联到用户

    # 关联用户
    user = relationship("User", back_populates="accounts")

    def to_dict(self):
        data = {
            'id': self.id,
            'email': self.email,
            'password': self.password,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'create_time': self.create_time,
            'expire_time': self.expire_time,
            'is_used': self.is_used,
            'is_deleted': self.is_deleted,
            'expire_time_fmt': datetime.fromtimestamp(self.expire_time).strftime('%Y-%m-%d %H:%M:%S')
        }

        data["user_id"] = self.user_id

        return data
