from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def validate_env(*, strict: bool | None = None) -> None:
    """
    Validate environment configuration and emit actionable warnings.

    By default this only logs warnings/errors. Set CONFIG_STRICT=true to turn
    certain errors into a startup failure.
    """

    if strict is None:
        strict = _truthy(os.getenv("CONFIG_STRICT"))

    errors: list[str] = []
    warnings: list[str] = []

    secret_key = (os.getenv("SECRET_KEY") or "").strip()
    if secret_key in {"your_secret_key", "change-me"}:
        warnings.append("SECRET_KEY 仍为示例值，生产环境请设置高强度随机密钥")
    if secret_key and len(secret_key) < 16:
        warnings.append("SECRET_KEY 长度过短，生产环境建议 ≥ 32 字符")

    admin_password = (os.getenv("ADMIN_PASSWORD") or "").strip()
    if admin_password in {"admin", "password", "123456"}:
        warnings.append("ADMIN_PASSWORD 过于简单，生产环境请修改为强密码")

    if _truthy(os.getenv("ALLOW_SELF_REGISTER", "true")):
        warnings.append("ALLOW_SELF_REGISTER=true：允许自助注册（生产环境建议关闭）")

    if _truthy(os.getenv("ALLOW_ADMIN_PASSWORD_EXPORT", "false")):
        warnings.append("ALLOW_ADMIN_PASSWORD_EXPORT=true：允许管理员导出密码（高风险）")

    if not (os.getenv("METRICS_TOKEN") or "").strip():
        warnings.append("未设置 METRICS_TOKEN：/metrics 将对任何访问者开放")

    encryption_key = (os.getenv("ACCOUNT_ENCRYPTION_KEY") or "").strip()
    if not encryption_key:
        warnings.append("未设置 ACCOUNT_ENCRYPTION_KEY：账号密码将以明文形式存储")
    else:
        try:
            from cryptography.fernet import Fernet

            Fernet(encryption_key.encode("utf-8"))
        except Exception:
            errors.append("ACCOUNT_ENCRYPTION_KEY 无效：无法初始化 Fernet（请检查格式/字符集）")

    admin_user_ids_raw = (os.getenv("ADMIN_USER_IDS") or "").strip()
    if admin_user_ids_raw:
        bad = []
        for part in admin_user_ids_raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                int(part)
            except ValueError:
                bad.append(part)
        if bad:
            warnings.append(f"ADMIN_USER_IDS 包含无效项（已忽略）：{', '.join(bad)}")

    db_migration_mode = (os.getenv("DB_MIGRATION_MODE") or "").strip().lower()
    if db_migration_mode and db_migration_mode not in {
        "create_all",
        "alembic",
        "migrate",
        "migration",
    }:
        warnings.append("DB_MIGRATION_MODE 值未知，将回退到 create_all")

    if not _truthy(os.getenv("RATE_LIMIT_ENABLED", "true")):
        warnings.append("RATE_LIMIT_ENABLED=false：已关闭限流（可能增加暴露面）")

    for item in warnings:
        logger.warning("配置警告: %s", item)

    for item in errors:
        logger.error("配置错误: %s", item)

    if errors and strict:
        raise RuntimeError("配置错误导致启动失败（已启用 CONFIG_STRICT=true）")
