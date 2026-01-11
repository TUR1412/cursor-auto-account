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

### 本地运行

```bash
python -m pip install -r requirements.txt
python app.py
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

### API 速查

- `POST /api/register` 注册
- `POST /api/login` 登录
- `GET /api/user` 获取当前用户信息（需要 Token）
- `POST /api/account` 导入账号（需要 Token）
- `GET /api/account` 发放一个未使用账号（需要 Token）
- `GET /api/accounts` 获取当前用户账号列表（需要 Token）
- `PUT /api/account/<id>/status` 更新账号使用状态（需要 Token）
- `PUT /api/account/<id>/delete` 删除账号（需要 Token）
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
- **Observability**: `X-Request-ID`, Prometheus metrics at `GET /metrics`, optional JSON logs
- **Quality gates**: built-in `pytest` tests and `ruff` lint checks
- **Web console**: `GET /app` (no framework, fast, Lighthouse-friendly)

### Quick Start

```bash
python -m pip install -r requirements.txt
python app.py
```

Open:

- `http://localhost:8001/app`
- `http://localhost:8001/metrics`

### Development

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest
```

---

## License

MIT
