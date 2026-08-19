from fastapi import Request

def get_client_ip(request: Request) -> str:
    """
    获取客户端真实 IP。
    优先从 X-Forwarded-For 头获取（支持代理），否则从 request.client.host 获取。
    """
    # 1. 如果经过 Nginx 等代理，通常会把真实 IP 放在 X-Forwarded-For 中
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # 取第一个 IP（最原始客户端）
        return forwarded.split(",")[0].strip()
    
    # 2. 直接获取连接地址（如果 request.client 存在）
    if request.client:
        return request.client.host
    
    # 3. 保底值（测试环境或异常情况）
    return "unknown"