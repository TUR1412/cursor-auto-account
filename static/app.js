/* Minimal vanilla JS console for the Flask API.
 *
 * Design goals:
 * - No framework / tiny payload
 * - Accessible feedback (aria-live)
 * - Token stored locally (demo-grade; tighten for production)
 */

const storageKey = "cursor_account_token";

function getToken() {
  return localStorage.getItem(storageKey) || "";
}

function setToken(token) {
  if (!token) return;
  localStorage.setItem(storageKey, token);
}

function clearToken() {
  localStorage.removeItem(storageKey);
}

function $(id) {
  return document.getElementById(id);
}

function showNotice(message, variant = "success") {
  const el = $("notice");
  if (!el) return;
  el.hidden = false;
  el.className = `notice notice--${variant}`;
  el.textContent = message;
}

function hideNotice() {
  const el = $("notice");
  if (!el) return;
  el.hidden = true;
  el.textContent = "";
  el.className = "notice";
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetch(path, { ...options, headers });
  const text = await resp.text();

  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { status: "error", message: text || "Invalid response" };
  }

  if (!resp.ok) {
    const msg = data?.message || `HTTP ${resp.status}`;
    const code = data?.code ? ` (${data.code})` : "";
    throw new Error(`${msg}${code}`);
  }

  return data;
}

function setAuthedUI(user) {
  $("authCard").hidden = true;
  $("appCard").hidden = false;
  $("btnLogout").hidden = false;
  $("navUser").textContent = `已登录：${user.username}（ID ${user.id}）`;
}

function setGuestUI() {
  $("authCard").hidden = false;
  $("appCard").hidden = true;
  $("btnLogout").hidden = true;
  $("navUser").textContent = "未登录";
}

function fmtExpire(account) {
  return account.expire_time_fmt || String(account.expire_time || "");
}

function fmtTime(epochSeconds) {
  if (!epochSeconds) return "";
  const d = new Date(Number(epochSeconds) * 1000);
  return d.toLocaleString();
}

function renderAccounts(accounts) {
  const tbody = $("accountsTable").querySelector("tbody");
  tbody.innerHTML = "";

  for (const acc of accounts) {
    const tr = document.createElement("tr");
    const usedPill = acc.is_used ? "pill pill--warn" : "pill pill--ok";
    const usedText = acc.is_used ? "Used" : "Free";

    tr.innerHTML = `
      <td>${acc.id}</td>
      <td><code>${acc.email}</code></td>
      <td><span class="${usedPill}">${usedText}</span></td>
      <td>${fmtExpire(acc)}</td>
      <td>
        <button class="btn btn--ghost btn--sm" data-action="copy" data-id="${acc.id}">复制</button>
        <button class="btn btn--ghost btn--sm" data-action="toggle" data-id="${acc.id}" data-used="${acc.is_used ? 1 : 0}">
          标记${acc.is_used ? "未用" : "已用"}
        </button>
        <button class="btn btn--danger btn--sm" data-action="delete" data-id="${acc.id}">删除</button>
      </td>
    `;
    tbody.appendChild(tr);
  }

  tbody.onclick = async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const action = btn.dataset.action;
    const id = btn.dataset.id;

    try {
      hideNotice();
      if (action === "copy") {
        const data = await api(`/api/account/${id}`);
        const acc = data.account;
        const text = `${acc.email}\n${acc.password}`;
        await navigator.clipboard.writeText(text);
        showNotice("已复制到剪贴板", "success");
        return;
      }

      if (action === "toggle") {
        const currentUsed = Number(btn.dataset.used || 0);
        const nextUsed = currentUsed ? 0 : 1;
        await api(`/api/account/${id}/status`, {
          method: "PUT",
          body: JSON.stringify({ is_used: nextUsed }),
        });
        await refreshAccounts();
        showNotice("账号状态已更新", "success");
        return;
      }

      if (action === "delete") {
        await api(`/api/account/${id}/delete`, { method: "PUT" });
        await refreshAccounts();
        showNotice("账号已删除", "success");
      }
    } catch (err) {
      showNotice(err.message || "操作失败", "error");
    }
  };
}

function renderLogs(logs) {
  const tbody = $("logsTable").querySelector("tbody");
  tbody.innerHTML = "";

  for (const log of logs) {
    let detailText = "";
    try {
      detailText = log.detail ? JSON.stringify(JSON.parse(log.detail)) : "";
    } catch {
      detailText = log.detail || "";
    }

    const entity = log.entity_type ? `${log.entity_type}#${log.entity_id || ""}` : "";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${fmtTime(log.created_at)}</td>
      <td><code>${log.action}</code></td>
      <td>${entity}</td>
      <td><code>${detailText}</code></td>
    `;
    tbody.appendChild(tr);
  }
}

async function refreshAccounts() {
  const data = await api("/api/accounts");
  const accounts = data.accounts || [];
  $("accountsMeta").textContent = `共 ${data.total ?? accounts.length} 条`;
  renderAccounts(accounts);
}

async function refreshLogs() {
  const data = await api("/api/audit/logs?per_page=10");
  renderLogs(data.logs || []);
}

async function bootstrap() {
  $("btnLogout").addEventListener("click", () => {
    clearToken();
    setGuestUI();
    showNotice("已退出登录", "success");
  });

  $("btnRefreshLogs").addEventListener("click", async () => {
    try {
      hideNotice();
      await refreshLogs();
      showNotice("日志已刷新", "success");
    } catch (err) {
      showNotice(err.message || "刷新失败", "error");
    }
  });

  $("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      hideNotice();
      const username = $("loginUsername").value.trim();
      const password = $("loginPassword").value;
      const data = await api("/api/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(data.token);
      const me = await api("/api/user");
      setAuthedUI(me.user);
      await refreshAccounts();
      await refreshLogs();
      showNotice("登录成功", "success");
    } catch (err) {
      showNotice(err.message || "登录失败", "error");
    }
  });

  $("registerForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      hideNotice();
      const username = $("registerUsername").value.trim();
      const email = $("registerEmail").value.trim();
      const password = $("registerPassword").value;
      const data = await api("/api/register", {
        method: "POST",
        body: JSON.stringify({ username, password, email: email || undefined }),
      });
      setToken(data.token);
      const me = await api("/api/user");
      setAuthedUI(me.user);
      await refreshAccounts();
      await refreshLogs();
      showNotice("注册成功", "success");
    } catch (err) {
      showNotice(err.message || "注册失败", "error");
    }
  });

  $("importForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      hideNotice();
      const email = $("importEmail").value.trim();
      const password = $("importPassword").value;
      await api("/api/account", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      $("importPassword").value = "";
      await refreshAccounts();
      showNotice("账号已导入", "success");
    } catch (err) {
      showNotice(err.message || "导入失败", "error");
    }
  });

  $("btnCheckout").addEventListener("click", async () => {
    try {
      hideNotice();
      const data = await api("/api/account");
      $("checkoutResult").textContent = JSON.stringify(data.account, null, 2);
      await refreshAccounts();
      await refreshLogs();
      showNotice("账号已发放（已自动标记为已用）", "success");
    } catch (err) {
      $("checkoutResult").textContent = "";
      showNotice(err.message || "获取失败", "error");
    }
  });

  $("btnRefresh").addEventListener("click", async () => {
    try {
      hideNotice();
      await refreshAccounts();
      showNotice("已刷新", "success");
    } catch (err) {
      showNotice(err.message || "刷新失败", "error");
    }
  });

  // Initial state
  const token = getToken();
  if (!token) {
    setGuestUI();
    return;
  }

  try {
    const me = await api("/api/user");
    setAuthedUI(me.user);
    await refreshAccounts();
    await refreshLogs();
  } catch {
    clearToken();
    setGuestUI();
  }
}

document.addEventListener("DOMContentLoaded", bootstrap);
