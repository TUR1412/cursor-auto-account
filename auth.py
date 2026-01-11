import time
import uuid
from functools import wraps

import jwt
from flask import jsonify, request

from models import User, db

# JWT密钥和过期时间将在app.py中设置
SECRET_KEY = None
TOKEN_EXPIRY_DAYS = 30

# 生成JWT Token
def generate_token(user_id):
    # 计算过期时间
    now = int(time.time())
    expires_at = now + (TOKEN_EXPIRY_DAYS * 24 * 60 * 60)
    
    # 创建JWT payload
    payload = {
        'user_id': user_id,
        'iat': now,  # 发行时间
        'exp': expires_at,  # 过期时间
        'jti': str(uuid.uuid4())  # JWT ID，确保唯一性
    }
    
    # 签名并返回token
    jwt_token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm='HS256'
    )
    
    return jwt_token

# Token验证装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 从请求头获取token
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        # 从cookie获取token
        if not token and 'token' in request.cookies:
            token = request.cookies.get('token')
            
        # 从请求参数获取token
        if not token and 'token' in request.args:
            token = request.args.get('token')
            
        if not token:
            return jsonify({'status': 'error', 'message': '需要认证令牌'}), 401
        
        try:
            # 解码验证token
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            
            # 获取用户
            user_id = payload.get('user_id')
            if not user_id:
                return jsonify({'status': 'error', 'message': '无效的令牌'}), 401
                
            current_user = db.session.get(User, user_id)
            if not current_user:
                return jsonify({'status': 'error', 'message': '用户不存在'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'status': 'error', 'message': '令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'status': 'error', 'message': '无效的令牌'}), 401   
        except Exception:
            return jsonify({'status': 'error', 'message': '验证令牌错误'}), 401
        
        # 将用户添加到请求上下文
        request.current_user = current_user
        return f(*args, **kwargs)
    
    return decorated

# 管理员认证装饰器
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 首先验证token
        token_decorator = token_required(lambda: None)
        result = token_decorator()
        if result is not None:
            return result
        
        # 检查是否为管理员 (这里简单地使用ID为1作为管理员)
        if request.current_user.id != 1:
            return jsonify({'status': 'error', 'message': '需要管理员权限'}), 403
            
        return f(*args, **kwargs)
    
    return decorated 
