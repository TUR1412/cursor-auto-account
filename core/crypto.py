import os

from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:"


def _get_fernet():
    key = os.getenv("ACCOUNT_ENCRYPTION_KEY")
    if not key:
        return None
    return Fernet(key.encode("utf-8"))


def encrypt_secret(value: str) -> str:
    """
    Encrypt a secret for at-rest storage.

    If `ACCOUNT_ENCRYPTION_KEY` is not configured, returns the value as-is.
    """

    fernet = _get_fernet()
    if not fernet:
        return value

    if value.startswith(_PREFIX):
        return value

    token = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt_secret(value: str) -> str:
    """
    Decrypt a secret previously produced by `encrypt_secret`.

    If the value is not encrypted (no prefix), it will be returned as-is.
    """

    if not value.startswith(_PREFIX):
        return value

    fernet = _get_fernet()
    if not fernet:
        raise RuntimeError("ACCOUNT_ENCRYPTION_KEY 未配置，无法解密已加密的账号密码")

    token = value[len(_PREFIX) :].encode("utf-8")
    try:
        return fernet.decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("账号密码解密失败：密钥不匹配或数据已损坏") from exc
