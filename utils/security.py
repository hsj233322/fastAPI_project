# utils/security.py
import bcrypt

def get_hash_password(password: str) -> str:
    """对密码进行哈希加密"""
    # 将字符串转成 bytes，然后加盐哈希，最后转回字符串
    salt = bcrypt.gensalt()
    pwd_bytes = password.encode("utf-8")
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验密码是否正确"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), 
        hashed_password.encode("utf-8")
    )