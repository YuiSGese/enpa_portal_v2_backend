from passlib.context import CryptContext

import bcrypt

def get_password_hash(password: str) -> str:
    """
    Hash password và trả về dạng string UTF-8
    """
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=10))
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    So sánh password người dùng nhập với hash trong DB
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))