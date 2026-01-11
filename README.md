# Account Manager（Flask）

[中文](#中文) · [English](#english)

---

## 中文

这是一个轻量级的账号管理服务（Flask + SQLAlchemy），提供 JWT 鉴权的 REST API 和一个极简 Web 控制台。

### ✅ 合规说明（重要）

本项目**不包含**也**不会执行**任何第三方账号自动注册、验证码/风控绕过、批量注册等逻辑。  
系统仅用于管理你**已合法拥有**的账号数据（导入 / 列表 / 发放 / 标记 / 删除）。

### 功能特性

- **JWT 鉴权**：注册/登录后获得 Token，支持 Header/Cookie/Query 三种携带方式
- **账号池管理**：导入账号后可“发放”一个未使用账号（发放即自动标记为已用）
- **可观测性**：
  - `X-Request-ID` 请求链路标识
  - Prometheus 指标 `GET /metrics`
  - 可选 JSON 日志（`LOG_FORMAT=json`）
- **审计日志**：记录关键操作并可查询（`GET /api/audit/logs`）
- **质量保障**：内置 `pytest` 单元测试 + `ruff` 静态检查
- **Web 控制台**：访问 `GET /app`（无框架、轻量、性能友好）

### 快速开始（Docker Compose）

1. 克隆仓库

```bash
git clone https://github.com/TUR1412/cursor-auto-account.git
cd cursor-auto-account
```

2. 配置环境变量（可选）

复制 `.env.example` 为 `.env` 并按需修改。

3. 启动

```bash
docker-compose up -d --build
```

4. 访问

- Web 控制台：`http://localhost:8001/app`
- 健康检查：`http://localhost:8001/api/health`
- 监控指标：`http://localhost:8001/metrics`
- 就绪探针（含DB检测）：`http://localhost:8001/api/health?ready=1`

### 本地运行

```bash
python -m pip install -r requirements.txt
python app.py
```

生产运行（推荐，使用 Waitress）：

```bash
waitress-serve --listen=0.0.0.0:8001 wsgi:app
```

> 本地/测试推荐使用 sqlite：设置 `DATABASE_URL=sqlite:///data.db`。

### 开发与自测

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest
```

### 环境变量

| 变量 | 说明 | 示例 |
|---|---|---|
| `DATABASE_URL` | 优先使用的 SQLAlchemy 连接串（推荐本地/测试） | `sqlite:///data.db` |
| `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` | MySQL 连接参数（未设置 `DATABASE_URL` 时使用） |  |
| `SECRET_KEY` | JWT 签名密钥 | `change-me` |
| `TOKEN_EXPIRY_DAYS` | Token 有效期（天） | `30` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `LOG_FORMAT` | 日志格式 | `text` / `json` |
| `METRICS_TOKEN` | 指标接口保护 Token（可选） | `your-token` |
| `ACCOUNT_ENCRYPTION_KEY` | 账号密码加密密钥（可选，建议生产环境配置） | `Fernet.generate_key()` |
| `RATE_LIMIT_ENABLED` | 轻量限流开关（可选） | `true` |
| `RATE_LIMIT_MAX_BUCKETS` | 限流内存桶上限（可选） | `5000` |
| `ALLOW_SELF_REGISTER` | 是否允许用户自助注册（可选） | `true` |
| `ALLOW_ADMIN_PASSWORD_EXPORT` | 是否允许管理员批量导出密码（强风险，默认关闭） | `false` |
| `ADMIN_USERNAME` | 管理员用户名（用于创建默认管理员 + 管理员权限识别） | `admin` |
| `ADMIN_PASSWORD` | 管理员密码（启动时会同步更新） | `admin` |
| `ADMIN_USER_IDS` | 管理员用户 ID 白名单（逗号分隔，可选） | `1,2` |

### API 速查

- `POST /api/register` 注册
- `POST /api/login` 登录
- `GET /api/user` 获取当前用户信息（需要 Token）
- `POST /api/account` 导入账号（需要 Token）
- `GET /api/account` 发放一个未使用账号（需要 Token）
- `GET /api/account/<id>` 获取单个账号详情（需要 Token）
- `GET /api/accounts` 获取当前用户账号列表（需要 Token，支持 `page` / `per_page` / `q` / `used`）
- `PUT /api/account/<id>/status` 更新账号使用状态（需要 Token）
- `PUT /api/account/<id>/delete` 删除账号（需要 Token）
- `GET /api/audit/logs` 获取当前用户审计日志（需要 Token）
- `GET /api/admin/audit/logs` 管理员审计日志（需要管理员 Token）
- `GET /api/health` 健康检查
- `GET /metrics` Prometheus 指标

---

## English

A lightweight account-management service built with Flask + SQLAlchemy. It exposes a JWT-protected REST API and a minimal web console.

### ✅ Compliance Notice (Important)

This project **does not** include or run any third-party account auto-registration, CAPTCHA/anti-bot bypass, or bulk-signup logic.  
It is intended to manage **accounts you already own legitimately** (import / list / checkout / mark / delete).

### Features

- **JWT authentication** (Header/Cookie/Query supported)
- **Account pool workflow**: import accounts, then “checkout” an unused one (checkout marks it as used)
- **Listing UX**: `/api/accounts` supports `page` / `per_page` / `q` / `used` for pagination and filtering
- **Observability**: `X-Request-ID`, Prometheus metrics at `GET /metrics`, optional JSON logs
- **Audit logs**: query at `GET /api/audit/logs`
- **Optional at-rest encryption**: `ACCOUNT_ENCRYPTION_KEY` (recommended for production)
- **Optional rate limiting**: `RATE_LIMIT_ENABLED`
- **Admin access control**: `ADMIN_USERNAME` / `ADMIN_USER_IDS`
- **Quality gates**: built-in `pytest` tests and `ruff` lint checks
- **Web console**: `GET /app` (no framework, fast, Lighthouse-friendly)

### Quick Start

```bash
python -m pip install -r requirements.txt
python app.py
```

Production (recommended, Waitress):

```bash
waitress-serve --listen=0.0.0.0:8001 wsgi:app
```

Open:

- `http://localhost:8001/app`
- `http://localhost:8001/metrics`
- `http://localhost:8001/api/health?ready=1` (readiness probe with DB check)

### Development

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest
```

---

## License

MIT
