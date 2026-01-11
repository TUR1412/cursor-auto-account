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


def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.get_data(as_text=True)

