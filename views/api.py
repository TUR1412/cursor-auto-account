import logging
import os
import threading
import time
import traceback
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from account_service import create_account_for_user
from auth import admin_required, generate_token, token_required
from core.audit import record_audit
from core.crypto import encrypt_secret
from core.ratelimit import rate_limit
from models import Account, AuditLog, User, db

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 设置日志
logger = logging.getLogger(__name__)

# 创建一个信号量用于限制并发请求
account_semaphore = threading.Semaphore(3)

# 限流装饰器
def limit_concurrency(semaphore):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 尝试获取信号量
            acquired = semaphore.acquire(blocking=False)
            if not acquired:
                # 如果没有获取到信号量，返回响应码 429 (Too Many Requests)
                logger.warning("并发请求数超过限制，拒绝处理请求")
                return jsonify({
                    'status': 'error',
                    'message': '服务器繁忙，请稍后再试'
                }), 429

            try:
                # 执行原函数
                return f(*args, **kwargs)
            finally:
                # 无论成功与否，释放信号量
                semaphore.release()
        return decorated_function
    return decorator

# 用户注册
@api_bp.route('/register', methods=['POST'])
@rate_limit(limit=10, window_seconds=60, key_prefix="register")
def register():
    try:
        if os.getenv("ALLOW_SELF_REGISTER", "true").lower() != "true":
            return jsonify({"status": "error", "message": "已禁用自助注册"}), 403

        data = request.json

        if not data or not data.get('username') or not data.get('password'):
            return jsonify({
                'status': 'error',
                'message': '请提供用户名和密码'
            }), 400

        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({
                'status': 'error',
                'message': '用户名已存在'
            }), 400

        # 创建新用户
        new_user = User(
            username=data['username'],
            password_hash=User.hash_password(data['password']),
            temp_email_address='zoowayss@mailto.plus',
            email=data.get('email'),
            created_at=int(time.time())
        )

        db.session.add(new_user)
        db.session.flush()
        record_audit(action="user.register", user=new_user, detail={"username": new_user.username})
        db.session.commit()

        # 生成token
        token = generate_token(new_user.id)

        return jsonify({
            'status': 'success',
            'message': '注册成功',
            'user': new_user.to_dict(),
            'token': token
        })

    except Exception:
        db.session.rollback()
        logger.error(f"注册失败: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': '注册失败，请稍后再试'}), 500

# 用户登录
@api_bp.route('/login', methods=['POST'])
@rate_limit(limit=30, window_seconds=60, key_prefix="login")
def login():
    try:
        data = request.json

        if not data or not data.get('username') or not data.get('password'):
            return jsonify({
                'status': 'error',
                'message': '请提供用户名和密码'
            }), 400

        # 查找用户
        user = User.query.filter_by(username=data['username']).first()
        if not user or not user.verify_password(data['password']):
            return jsonify({
                'status': 'error',
                'message': '用户名或密码错误'
            }), 401

        # 更新最后登录时间
        user.last_login = int(time.time())
        record_audit(action="user.login", user=user, detail={"username": user.username})
        db.session.commit()

        # 生成token
        token = generate_token(user.id)

        return jsonify({
            'status': 'success',
            'message': '登录成功',
            'user': user.to_dict(),
            'token': token
        })

    except Exception:
        logger.error(f"登录失败: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': '登录失败，请稍后再试'}), 500

# 获取用户信息
@api_bp.route('/user', methods=['GET'])
@token_required
def get_user_info():
    return jsonify({
        'status': 'success',
        'user': request.current_user.to_dict()
    })

# 退出登录
@api_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    # 无需数据库操作，客户端清除token即可
    return jsonify({
        'status': 'success',
        'message': '已成功退出登录'
    })

# 获取一个可用账号 (已登录用户)
@api_bp.route('/account', methods=['GET'])
@token_required
@limit_concurrency(account_semaphore)
def get_account():
    try:
        logger.info(f"用户 {request.current_user.id} 请求获取账号")
        result = create_account_for_user(request.current_user)
        if result.get('status') == 'success':
            account = result.get("account") or {}
            record_audit(
                action="account.checkout",
                user=request.current_user,
                entity_type="account",
                entity_id=account.get("id"),
                detail={"email": account.get("email")},
            )
            db.session.commit()
            return jsonify(result), 200
        if result.get("code") == "NO_AVAILABLE_ACCOUNT":
            return jsonify(result), 404
        return jsonify(result), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"获取账号失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '获取账号失败，请稍后再试'
        }), 500

# 导入账号（已登录用户）
@api_bp.route('/account', methods=['POST'])
@token_required
def import_account():
    try:
        data = request.json or {}

        email = (data.get("email") or "").strip()
        password = data.get("password")
        if not email or not password:
            return jsonify({"status": "error", "message": "缺少必要参数: email/password"}), 400

        first_name = data.get("first_name")
        last_name = data.get("last_name")

        now = int(time.time())
        expire_time = data.get("expire_time")
        if expire_time is not None:
            expire_time = int(expire_time)
        else:
            expire_days = int(data.get("expire_days", 15))
            expire_time = now + (expire_days * 24 * 60 * 60)

        account = Account(
            email=email,
            password=encrypt_secret(password),
            first_name=first_name,
            last_name=last_name,
            create_time=now,
            expire_time=expire_time,
            is_used=int(data.get("is_used", 0)),
            is_deleted=0,
            user_id=request.current_user.id,
        )

        db.session.add(account)
        db.session.flush()
        record_audit(
            action="account.import",
            user=request.current_user,
            entity_type="account",
            entity_id=account.id,
            detail={"email": account.email},
        )
        db.session.commit()

        return (
            jsonify({"status": "success", "message": "账号已导入", "account": account.to_dict()}),
            201,
        )

    except IntegrityError:
        db.session.rollback()
        return jsonify({"status": "error", "message": "该邮箱已存在，无法重复导入"}), 409
    except Exception:
        db.session.rollback()
        logger.error(f"导入账号失败: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": "导入账号失败，请稍后再试"}), 500

# 获取用户的所有账号
@api_bp.route('/accounts', methods=['GET'])
@token_required
def get_user_accounts():
    try:
        user_id = request.current_user.id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # 查询用户的账号 - 只查询明确归属于该用户且未被删除的账号
        query = Account.query.filter_by(user_id=user_id, is_deleted=0).order_by(Account.create_time.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        accounts = [account.to_dict() for account in pagination.items]

        return jsonify({
            'status': 'success',
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'total_pages': pagination.pages,
            'accounts': accounts
        })

    except Exception:
        logger.error(f"获取用户账号失败: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': '获取账号列表失败，请稍后再试'}), 500

# 获取单个账号详情（需要权限）
@api_bp.route("/account/<int:account_id>", methods=["GET"])
@token_required
def get_account_detail(account_id):
    account = db.session.get(Account, account_id)
    if not account or account.is_deleted == 1:
        return jsonify({"status": "error", "message": f"账号 ID {account_id} 不存在"}), 404

    user = request.current_user
    if account.user_id is not None and account.user_id != user.id and user.id != 1:
        return jsonify({"status": "error", "message": "无权查看此账号"}), 403

    record_audit(
        action="account.reveal",
        user=user,
        entity_type="account",
        entity_id=account.id,
        detail={"email": account.email},
    )
    db.session.commit()

    return jsonify({"status": "success", "account": account.to_dict(include_password=True)}), 200


# 修改账号使用状态
@api_bp.route('/account/<int:account_id>/status', methods=['PUT'])
@token_required
def update_account_status(account_id):
    try:
        # 获取请求数据
        data = request.json
        if data is None or 'is_used' not in data:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400

        # 查找账号
        account = db.session.get(Account, account_id)
        if not account:
            return jsonify({
                'status': 'error',
                'message': f'账号 ID {account_id} 不存在'
            }), 404

        # 检查用户权限
        user = request.current_user

        # 严格检查账号所有权 - 只有明确归属于当前用户或管理员的账号才能修改
        # 不再自动归属无主账号
        if account.user_id is None:
            if user.id == 1:  # 管理员可以处理无主账号
                account.user_id = user.id  # 管理员可以认领无主账号
            else:
                return jsonify({
                    'status': 'error',
                    'message': '无权修改此账号'
                }), 403
        elif account.user_id != user.id and user.id != 1:
            return jsonify({
                'status': 'error',
                'message': '无权修改此账号'
                }), 403

        # 更新状态
        account.is_used = data['is_used']
        record_audit(
            action="account.update_status",
            user=request.current_user,
            entity_type="account",
            entity_id=account.id,
            detail={"is_used": int(account.is_used)},
        )
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': '账号状态已更新',
            'account': account.to_dict()
        })

    except Exception:
        db.session.rollback()
        logger.error(f"更新账号状态失败: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': '更新账号状态失败，请稍后再试'
        }), 500

# 管理员获取所有账号
@api_bp.route('/admin/accounts', methods=['GET'])
@admin_required
def admin_get_accounts():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        include_password = request.args.get("include_password", "false").lower() == "true"
        if include_password and os.getenv("ALLOW_ADMIN_PASSWORD_EXPORT", "false").lower() != "true":
            record_audit(action="admin.password_export.blocked", user=request.current_user)
            db.session.commit()
            return jsonify({"status": "error", "message": "已禁用管理员批量导出密码"}), 403

        # 获取查询参数，是否包含已删除的账号
        show_deleted = request.args.get('show_deleted', 'false').lower() == 'true'

        # 构建查询
        query = Account.query

        # 如果不显示已删除账号，则添加过滤条件
        if not show_deleted:
            query = query.filter_by(is_deleted=0)

        # 计算总页数
        total_accounts = query.count()
        total_pages = (total_accounts + per_page - 1) // per_page

        # 获取当前页的账号数据，按照create_time倒序排列
        accounts = query.order_by(Account.create_time.desc()).paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'status': 'success',
            'page': page,
            'per_page': per_page,
            'total': total_accounts,
            'total_pages': total_pages,
            'accounts': [account.to_dict(include_password=include_password) for account in accounts.items]
        })

    except Exception:
        logger.error(f"管理员获取所有账号失败: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': '获取账号列表失败，请稍后再试'}), 500

# 管理员获取所有用户
@api_bp.route('/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # 查询用户 倒序排列
        query = User.query.order_by(User.id.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        users = [user.to_dict() for user in pagination.items]

        return jsonify({
            'status': 'success',
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'total_pages': pagination.pages,
            'users': users
        })

    except Exception:
        logger.error(f"管理员获取所有用户失败: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': '获取用户列表失败，请稍后再试'}), 500

# 逻辑删除账号
@api_bp.route('/account/<int:account_id>/delete', methods=['PUT'])
@token_required
def delete_account(account_id):
    try:
        # 查找账号
        account = db.session.get(Account, account_id)
        if not account:
            return jsonify({
                'status': 'error',
                'message': f'账号 ID {account_id} 不存在'
            }), 404

        # 检查用户权限
        user = request.current_user

        # 严格检查账号所有权 - 只有明确归属于当前用户或管理员的账号才能删除
        if account.user_id is None:
            if user.id == 1:  # 管理员可以处理无主账号
                pass
            else:
                return jsonify({
                    'status': 'error',
                    'message': '无权删除此账号'
                }), 403
        elif account.user_id != user.id and user.id != 1:
            return jsonify({
                'status': 'error',
                'message': '无权删除此账号'
            }), 403

        # 更新删除状态
        account.is_deleted = 1
        record_audit(
            action="account.delete",
            user=request.current_user,
            entity_type="account",
            entity_id=account.id,
            detail={"email": account.email},
        )
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': '账号已删除',
            'account': account.to_dict()
        })

    except Exception:
        db.session.rollback()
        logger.error(f"删除账号失败: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': '删除账号失败，请稍后再试'
        }), 500

# 健康检查
@api_bp.route('/health', methods=['GET'])
def health_check():
    payload = {'status': 'ok', 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    # Readiness probe: check database connectivity only when requested.
    ready = request.args.get("ready", "false").lower() in {"1", "true", "yes"}
    if ready:
        try:
            db.session.execute(text("SELECT 1"))
            payload["db"] = "ok"
            return jsonify(payload), 200
        except Exception:
            payload["status"] = "error"
            payload["db"] = "error"
            return jsonify(payload), 503

    return jsonify(payload), 200

@api_bp.route('/user/<int:user_id>', methods=['PUT'])
@token_required
def update_user(user_id):
    try:
        # 记录调试信息
        logger.info(f"更新用户请求 - 当前用户ID: {request.current_user.id}")

        # 检查权限
        if request.current_user.id != user_id and not request.current_user.is_admin:
            logger.warning(f"权限不足 - 当前用户ID: {request.current_user.id}, 目标用户ID: {user_id}")
            return jsonify({
                'status': 'error',
                'message': '无权修改其他用户信息'
            }), 403

        # 获取请求数据
        data = request.json
        if not data:
            logger.warning("缺少更新数据")
            return jsonify({
                'status': 'error',
                'message': '缺少更新数据'
            }), 400

        # 查找用户
        user = db.session.get(User, user_id)
        if not user:
            logger.warning(f"用户不存在 - 用户ID: {user_id}")
            return jsonify({
                'status': 'error',
                'message': '用户不存在'
            }), 404

        # 更新用户信息
        if 'domain' in data:
            user.domain = data['domain']
        if 'temp_email_address' in data:
            if '@' in data['temp_email_address']:
                user.temp_email_address = data['temp_email_address']
            else:
                raise ValueError('临时邮箱地址格式错误 正确格式：zoowayss@mailto.plus')
        if 'email' in data:
            user.email = data['email']
        if 'password' in data:
            user.password_hash = User.hash_password(data['password'])

        record_audit(
            action="user.update",
            user=request.current_user,
            entity_type="user",
            entity_id=user.id,
        )
        db.session.commit()
        logger.info(f"用户信息更新成功 - 用户ID: {user_id}")

        return jsonify({
            'status': 'success',
            'message': '用户信息更新成功',
            'user': user.to_dict()
        })

    except ValueError as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception:
        db.session.rollback()
        logger.error(f"更新用户信息失败: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': '更新用户信息失败，请稍后再试'
        }), 500


# 获取当前用户的审计日志
@api_bp.route("/audit/logs", methods=["GET"])
@token_required
def get_audit_logs():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = AuditLog.query.filter_by(user_id=request.current_user.id).order_by(
        AuditLog.created_at.desc()
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "status": "success",
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "total_pages": pagination.pages,
            "logs": [log.to_dict() for log in pagination.items],
        }
    )


# 管理员获取审计日志
@api_bp.route("/admin/audit/logs", methods=["GET"])
@admin_required
def admin_get_audit_logs():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    user_id = request.args.get("user_id", None, type=int)

    query = AuditLog.query
    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    query = query.order_by(AuditLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "status": "success",
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "total_pages": pagination.pages,
            "logs": [log.to_dict() for log in pagination.items],
        }
    )
