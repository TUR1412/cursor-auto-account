def _register(client, username="alice", password="passw0rd", email="alice@example.com"):
    return client.post(
        "/api/register",
        json={"username": username, "password": password, "email": email},
    )


def _login(client, username="alice", password="passw0rd"):
    return client.post("/api/login", json={"username": username, "password": password})


def _auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"

    ready = client.get("/api/health?ready=1")
    assert ready.status_code == 200
    assert ready.json["db"] == "ok"


def test_register_login_and_user_info(client):
    resp = _register(client)
    assert resp.status_code == 200
    assert resp.json["status"] == "success"
    assert resp.json["token"]

    token = resp.json["token"]
    me = client.get("/api/user", headers=_auth_headers(token))
    assert me.status_code == 200
    assert me.json["status"] == "success"
    assert me.json["user"]["username"] == "alice"

    login = _login(client)
    assert login.status_code == 200
    assert login.json["status"] == "success"
    assert login.json["token"]


def test_import_and_checkout_account_flow(client):
    reg = _register(client, username="bob", password="p@ss", email="bob@example.com")
    token = reg.json["token"]

    imported = client.post(
        "/api/account",
        headers=_auth_headers(token),
        json={"email": "acc@example.com", "password": "accpass", "expire_days": 1},
    )
    assert imported.status_code == 201
    assert imported.json["status"] == "success"
    account_id = imported.json["account"]["id"]

    detail = client.get(f"/api/account/{account_id}", headers=_auth_headers(token))
    assert detail.status_code == 200
    assert detail.json["status"] == "success"
    assert detail.json["account"]["password"]

    checkout = client.get("/api/account", headers=_auth_headers(token))
    assert checkout.status_code == 200
    assert checkout.json["status"] == "success"
    assert checkout.json["account"]["email"] == "acc@example.com"
    assert checkout.json["account"]["is_used"] == 1

    none_left = client.get("/api/account", headers=_auth_headers(token))
    assert none_left.status_code == 404
    assert none_left.json["status"] == "error"
    assert none_left.json["code"] == "NO_AVAILABLE_ACCOUNT"

    accounts = client.get("/api/accounts", headers=_auth_headers(token))
    assert accounts.status_code == 200
    assert accounts.json["status"] == "success"
    assert len(accounts.json["accounts"]) == 1
    assert accounts.json["accounts"][0]["id"] == account_id

    # Audit logs should include key actions
    logs = client.get("/api/audit/logs?per_page=20", headers=_auth_headers(token))
    assert logs.status_code == 200
    actions = {item["action"] for item in logs.json["logs"]}
    assert "user.register" in actions
    assert "account.import" in actions
    assert "account.checkout" in actions


def test_accounts_query_and_pagination(client):
    reg = _register(client, username="query_user", password="p@ss", email="q@example.com")
    token = reg.json["token"]

    emails = [
        "alpha@example.com",
        "beta@example.com",
        "alpha-beta@example.com",
    ]
    for email in emails:
        imported = client.post(
            "/api/account",
            headers=_auth_headers(token),
            json={"email": email, "password": "accpass", "expire_days": 1},
        )
        assert imported.status_code == 201

    filtered = client.get("/api/accounts?q=alpha&per_page=10", headers=_auth_headers(token))
    assert filtered.status_code == 200
    assert filtered.json["status"] == "success"
    assert filtered.json["total"] == 2
    assert all("alpha" in item["email"] for item in filtered.json["accounts"])

    page1 = client.get("/api/accounts?per_page=1&page=1", headers=_auth_headers(token))
    assert page1.status_code == 200
    assert page1.json["status"] == "success"
    assert page1.json["total"] == 3
    assert page1.json["total_pages"] == 3
    assert len(page1.json["accounts"]) == 1

    page2 = client.get("/api/accounts?per_page=1&page=2", headers=_auth_headers(token))
    assert page2.status_code == 200
    assert page2.json["status"] == "success"
    assert page2.json["total"] == 3
    assert len(page2.json["accounts"]) == 1


def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.get_data(as_text=True)


def test_openapi_and_docs_routes(client):
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    assert spec.is_json
    assert spec.json["openapi"].startswith("3.")
    assert "/api/login" in spec.json["paths"]

    docs = client.get("/docs")
    assert docs.status_code == 200
    text = docs.get_data(as_text=True)
    assert "/openapi.json" in text


def test_account_password_encryption_at_rest(app, client, monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ACCOUNT_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))

    reg = _register(client, username="enc_user", password="p@ss", email="enc@example.com")
    token = reg.json["token"]

    imported = client.post(
        "/api/account",
        headers=_auth_headers(token),
        json={"email": "enc-acc@example.com", "password": "encpass", "expire_days": 1},
    )
    assert imported.status_code == 201
    account_id = imported.json["account"]["id"]

    # Stored value should be encrypted (prefixed), but revealed value should be plaintext.
    from models import Account, db

    with app.app_context():
        stored = db.session.get(Account, account_id)
        assert stored.password.startswith("enc:")

    reveal = client.get(f"/api/account/{account_id}", headers=_auth_headers(token))
    assert reveal.status_code == 200
    assert reveal.json["account"]["password"] == "encpass"


def _make_client(tmp_path, monkeypatch, **env):
    from app import create_app
    from models import db

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("TOKEN_EXPIRY_DAYS", "30")

    for k, v in env.items():
        monkeypatch.setenv(k, str(v))

    application = create_app()
    application.config.update(TESTING=True)

    with application.app_context():
        db.create_all()

    return application.test_client()


def test_metrics_token_protection(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, METRICS_TOKEN="secret-token")

    unauth = client.get("/metrics")
    assert unauth.status_code == 401

    ok = client.get("/metrics", headers={"Authorization": "Bearer secret-token"})
    assert ok.status_code == 200


def test_self_register_can_be_disabled(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, ALLOW_SELF_REGISTER="false")
    resp = _register(client, username="u1", password="p1", email="u1@example.com")
    assert resp.status_code == 403


def test_admin_password_export_is_gated(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)

    reg = _register(client, username="admin", password="p", email="a@example.com")
    token = reg.json["token"]

    imported = client.post(
        "/api/account",
        headers=_auth_headers(token),
        json={"email": "acc2@example.com", "password": "accpass2", "expire_days": 1},
    )
    assert imported.status_code == 201

    blocked = client.get(
        "/api/admin/accounts?include_password=true",
        headers=_auth_headers(token),
    )
    assert blocked.status_code == 403

    monkeypatch.setenv("ALLOW_ADMIN_PASSWORD_EXPORT", "true")
    allowed = client.get(
        "/api/admin/accounts?include_password=true",
        headers=_auth_headers(token),
    )
    assert allowed.status_code == 200
    assert allowed.json["accounts"][0]["password"] == "accpass2"


def test_admin_required_respects_admin_username_and_ids(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, ADMIN_USERNAME="root")

    reg = _register(client, username="admin", password="p", email="a2@example.com")
    token = reg.json["token"]

    blocked = client.get("/api/admin/users", headers=_auth_headers(token))
    assert blocked.status_code == 403

    me = client.get("/api/user", headers=_auth_headers(token))
    assert me.status_code == 200
    user_id = me.json["user"]["id"]

    monkeypatch.setenv("ADMIN_USER_IDS", str(user_id))
    allowed = client.get("/api/admin/users", headers=_auth_headers(token))
    assert allowed.status_code == 200


def test_update_user_admin_gate_respects_config(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, ADMIN_USERNAME="root")

    reg1 = _register(client, username="admin", password="p", email="u1@example.com")
    token1 = reg1.json["token"]

    reg2 = _register(client, username="bob", password="p", email="u2@example.com")
    assert reg2.status_code == 200

    me2 = client.get("/api/user", headers=_auth_headers(reg2.json["token"]))
    user2_id = me2.json["user"]["id"]

    blocked = client.put(
        f"/api/user/{user2_id}",
        headers=_auth_headers(token1),
        json={"domain": "example.com"},
    )
    assert blocked.status_code == 403

    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    allowed = client.put(
        f"/api/user/{user2_id}",
        headers=_auth_headers(token1),
        json={"domain": "example.com"},
    )
    assert allowed.status_code == 200
