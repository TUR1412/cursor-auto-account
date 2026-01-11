from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from core.admin import is_admin_user
from core.crypto import decrypt_secret

db = SQLAlchemy()


# 用户模型
class User(db.Model):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    last_login = Column(BigInteger, nullable=True)
    domain = Column(String(255), default="zoowayss.top")
    temp_email_address = Column(String(255), default="zoowayss@mailto.plus", nullable=True)

    # 关联用户的账号
    accounts = relationship("Account", back_populates="user")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "domain": self.domain,
            "temp_email_address": self.temp_email_address,
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
        return is_admin_user(self)


# 定义账号模型
class Account(db.Model):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    create_time = Column(BigInteger, nullable=False)
    expire_time = Column(BigInteger, nullable=False)
    is_used = Column(Integer, default=0)  # 0: 未使用, 1: 已使用
    is_deleted = Column(Integer, default=0)  # 0: 未删除, 1: 已删除
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 关联到用户

    # 关联用户
    user = relationship("User", back_populates="accounts")

    def to_dict(self, include_password: bool = False):
        data = {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "create_time": self.create_time,
            "expire_time": self.expire_time,
            "is_used": self.is_used,
            "is_deleted": self.is_deleted,
            "expire_time_fmt": datetime.fromtimestamp(self.expire_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

        if include_password:
            data["password"] = decrypt_secret(self.password)

        data["user_id"] = self.user_id

        return data


class RevokedToken(db.Model):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    jti = Column(String(64), unique=True, nullable=False, index=True)
    exp = Column(BigInteger, nullable=False, index=True)
    revoked_at = Column(BigInteger, nullable=False, index=True)

    user = relationship("User")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=True)
    entity_id = Column(Integer, nullable=True)
    request_id = Column(String(64), nullable=False, index=True)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False, index=True)

    user = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "request_id": self.request_id,
            "ip": self.ip,
            "user_agent": self.user_agent,
            "detail": self.detail,
            "created_at": self.created_at,
        }
