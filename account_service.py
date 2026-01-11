from models import Account, db


def create_account_for_user(current_user):
    """
    为用户提供一个可用账号。

    合规说明：本项目不再自动注册第三方账号，也不包含/不执行任何验证码或风控绕过流程。
    该方法仅从数据库中“发放”用户已导入的账号（账号来源需由用户自行确保合法合规）。
    """

    try:
        # 取一个未使用且未删除的账号
        account = (
            Account.query.filter_by(user_id=current_user.id, is_deleted=0, is_used=0)
            .order_by(Account.create_time.desc())
            .first()
        )
        if not account:
            return {
                "status": "error",
                "code": "NO_AVAILABLE_ACCOUNT",
                "message": "没有可用账号，请先导入账号（POST /api/account）或联系管理员分配。",
            }

        # 发放即标记为已使用，避免重复发放
        account.is_used = 1
        db.session.commit()

        return {
            "status": "success",
            "message": "账号已发放",
            "account": account.to_dict(),
        }

    except Exception as exc:
        db.session.rollback()
        return {"status": "error", "code": "INTERNAL_ERROR", "message": str(exc)}
