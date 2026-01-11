/* Minimal vanilla JS console for the Flask API.
 *
 * Design goals:
 * - No framework / tiny payload
 * - Accessible feedback (aria-live)
 * - Token stored locally (demo-grade; tighten for production)
 */

const storageKey = "cursor_account_token";

const accountsState = {
  page: 1,
  perPage: 10,
  query: "",
};

const logsState = {
  page: 1,
  perPage: 20,
  query: "",
};

const usersState = {
  page: 1,
  perPage: 10,
  query: "",
};

const adminLogsState = {
  page: 1,
  perPage: 20,
  userId: "",
  query: "",
};

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

function escapeHtml(value) {
  const s = String(value ?? "");
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
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

function normalizeErrorMessage(err) {
  if (!err) return "未知错误";
  if (typeof err === "string") return err;
  if (err.message) return err.message;
  try {
    return JSON.stringify(err);
  } catch {
    return "未知错误";
  }
}

window.addEventListener("error", (event) => {
  try {
    const message = normalizeErrorMessage(event?.error) || String(event?.message || "");
    if (message) showNotice(message, "error");
  } catch {
    // ignore
  }
});

window.addEventListener("unhandledrejection", (event) => {
  try {
    const message = normalizeErrorMessage(event?.reason);
    if (message) showNotice(message, "error");
  } catch {
    // ignore
  }
});

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

function setAdminUI(user) {
  const adminCard = $("adminCard");
  if (!adminCard) return;
  adminCard.hidden = !(user && user.is_admin);
}

function setAuthedUI(user) {
  const authCard = $("authCard");
  const appCard = $("appCard");
  const btnLogout = $("btnLogout");
  const navUser = $("navUser");

  if (authCard) authCard.hidden = true;
  if (appCard) appCard.hidden = false;
  if (btnLogout) btnLogout.hidden = false;
  if (navUser) {
    const adminBadge = user?.is_admin ? " · Admin" : "";
    navUser.textContent = `已登录：${user.username}（ID ${user.id}）${adminBadge}`;
  }
  setAdminUI(user);
}

function setGuestUI() {
  const authCard = $("authCard");
  const appCard = $("appCard");
  const btnLogout = $("btnLogout");
  const navUser = $("navUser");

  if (authCard) authCard.hidden = false;
  if (appCard) appCard.hidden = true;
  if (btnLogout) btnLogout.hidden = true;
  if (navUser) navUser.textContent = "未登录";
  setAdminUI(null);
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
      <td><code>${escapeHtml(acc.email)}</code></td>
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
      <td><code>${escapeHtml(log.action)}</code></td>
      <td>${escapeHtml(entity)}</td>
      <td><code>${escapeHtml(detailText)}</code></td>
    `;
    tbody.appendChild(tr);
  }
}

function renderUsers(users) {
  const tbody = $("usersTable").querySelector("tbody");
  tbody.innerHTML = "";

  for (const user of users) {
    const tr = document.createElement("tr");
    const email = user.email ? String(user.email) : "";
    tr.innerHTML = `
      <td>${user.id}</td>
      <td><code>${escapeHtml(user.username)}</code></td>
      <td><code>${escapeHtml(email)}</code></td>
      <td>${fmtTime(user.created_at)}</td>
      <td>${fmtTime(user.last_login)}</td>
    `;
    tbody.appendChild(tr);
  }
}

function renderAdminLogs(logs) {
  const tbody = $("adminLogsTable").querySelector("tbody");
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
      <td>${escapeHtml(log.user_id ?? "")}</td>
      <td><code>${escapeHtml(log.action)}</code></td>
      <td>${escapeHtml(entity)}</td>
      <td><code>${escapeHtml(log.request_id || "")}</code></td>
      <td><code>${escapeHtml(detailText)}</code></td>
    `;
    tbody.appendChild(tr);
  }
}

async function refreshAccounts() {
  const params = new URLSearchParams();
  params.set("page", String(accountsState.page));
  params.set("per_page", String(accountsState.perPage));
  if (accountsState.query) params.set("q", accountsState.query);

  const data = await api(`/api/accounts?${params.toString()}`);
  const accounts = data.accounts || [];

  // If the current page becomes empty (e.g. after deletions), step back one
  // page and retry once.
  if (accounts.length === 0 && Number(data.page) > 1) {
    accountsState.page = Number(data.page) - 1;
    return refreshAccounts();
  }

  const total = Number(data.total ?? accounts.length);
  const page = Number(data.page ?? accountsState.page);
  const totalPages = Number(data.total_pages ?? 1) || 1;

  const meta = $("accountsMeta");
  if (meta) meta.textContent = `共 ${total} 条 · 每页 ${accountsState.perPage} 条`;

  const pager = $("accountsPager");
  if (pager) pager.textContent = `第 ${page}/${totalPages} 页`;

  const prev = $("btnPrevPage");
  if (prev) prev.disabled = page <= 1;

  const next = $("btnNextPage");
  if (next) next.disabled = page >= totalPages;

  renderAccounts(accounts);
}

async function refreshUsers() {
  const params = new URLSearchParams();
  params.set("page", String(usersState.page));
  params.set("per_page", String(usersState.perPage));
  if (usersState.query) params.set("q", usersState.query);

  const data = await api(`/api/admin/users?${params.toString()}`);
  const users = data.users || [];

  // If the current page becomes empty (e.g. after deletions), step back one
  // page and retry once.
  if (users.length === 0 && Number(data.page) > 1) {
    usersState.page = Number(data.page) - 1;
    return refreshUsers();
  }

  const total = Number(data.total ?? users.length);
  const page = Number(data.page ?? usersState.page);
  const totalPages = Number(data.total_pages ?? 1) || 1;

  const meta = $("usersMeta");
  if (meta) meta.textContent = `共 ${total} 条 · 每页 ${usersState.perPage} 条`;

  const pager = $("usersPager");
  if (pager) pager.textContent = `第 ${page}/${totalPages} 页`;

  const prev = $("btnUsersPrev");
  if (prev) prev.disabled = page <= 1;

  const next = $("btnUsersNext");
  if (next) next.disabled = page >= totalPages;

  renderUsers(users);
}

async function refreshAdminLogs() {
  const params = new URLSearchParams();
  params.set("page", String(adminLogsState.page));
  params.set("per_page", String(adminLogsState.perPage));
  const userId = String(adminLogsState.userId || "").trim();
  if (userId) params.set("user_id", userId);
  const query = String(adminLogsState.query || "").trim();
  if (query) params.set("q", query);

  const data = await api(`/api/admin/audit/logs?${params.toString()}`);
  const logs = data.logs || [];

  // If the current page becomes empty (e.g. after deletions), step back one
  // page and retry once.
  if (logs.length === 0 && Number(data.page) > 1) {
    adminLogsState.page = Number(data.page) - 1;
    return refreshAdminLogs();
  }

  const total = Number(data.total ?? logs.length);
  const page = Number(data.page ?? adminLogsState.page);
  const totalPages = Number(data.total_pages ?? 1) || 1;

  const meta = $("adminLogsMeta");
  if (meta) meta.textContent = `共 ${total} 条 · 每页 ${adminLogsState.perPage} 条`;

  const pager = $("adminLogsPager");
  if (pager) pager.textContent = `第 ${page}/${totalPages} 页`;

  const prev = $("btnAdminLogsPrev");
  if (prev) prev.disabled = page <= 1;

  const next = $("btnAdminLogsNext");
  if (next) next.disabled = page >= totalPages;

  renderAdminLogs(logs);
}

async function refreshLogs() {
  const params = new URLSearchParams();
  params.set("page", String(logsState.page));
  params.set("per_page", String(logsState.perPage));
  if (logsState.query) params.set("q", logsState.query);

  const data = await api(`/api/audit/logs?${params.toString()}`);
  const logs = data.logs || [];

  // If the current page becomes empty, step back one page and retry once.
  if (logs.length === 0 && Number(data.page) > 1) {
    logsState.page = Number(data.page) - 1;
    return refreshLogs();
  }

  const total = Number(data.total ?? logs.length);
  const page = Number(data.page ?? logsState.page);
  const totalPages = Number(data.total_pages ?? 1) || 1;

  const meta = $("logsMeta");
  if (meta) meta.textContent = `共 ${total} 条 · 每页 ${logsState.perPage} 条`;

  const pager = $("logsPager");
  if (pager) pager.textContent = `第 ${page}/${totalPages} 页`;

  const prev = $("btnLogsPrev");
  if (prev) prev.disabled = page <= 1;

  const next = $("btnLogsNext");
  if (next) next.disabled = page >= totalPages;

  renderLogs(logs);
}

async function bootstrap() {
  const isAppPage = Boolean($("loginForm") && $("appCard"));
  const perPageSelect = $("accountsPerPage");
  const logsPerPageSelect = $("logsPerPage");
  const usersPerPageSelect = $("usersPerPage");
  const adminLogsPerPageSelect = $("adminLogsPerPage");

  // Global navbar actions (available on all pages)
  const btnLogout = $("btnLogout");
  if (btnLogout) {
    btnLogout.addEventListener("click", async () => {
      try {
        hideNotice();
        if (getToken()) {
          await api("/api/logout", { method: "POST" });
        }
      } catch {
        // best-effort, still clear local token
      } finally {
        clearToken();
        setGuestUI();
        showNotice("已退出登录", "success");
      }
    });
  }

  if (isAppPage && perPageSelect) {
    accountsState.perPage = Number(perPageSelect.value || 10) || 10;
  }

  if (isAppPage && logsPerPageSelect) {
    logsState.perPage = Number(logsPerPageSelect.value || 20) || 20;
  }

  if (isAppPage && usersPerPageSelect) {
    usersState.perPage = Number(usersPerPageSelect.value || 10) || 10;
  }

  if (isAppPage && adminLogsPerPageSelect) {
    adminLogsState.perPage = Number(adminLogsPerPageSelect.value || 20) || 20;
  }

  let queryTimer = null;
  const queryInput = $("accountsQuery");
  if (queryInput) {
    queryInput.addEventListener("input", () => {
      if (queryTimer) window.clearTimeout(queryTimer);
      queryTimer = window.setTimeout(async () => {
        try {
          hideNotice();
          accountsState.query = queryInput.value.trim();
          accountsState.page = 1;
          await refreshAccounts();
        } catch (err) {
          showNotice(err.message || "搜索失败", "error");
        }
      }, 250);
    });
  }

  let logsQueryTimer = null;
  const logsQueryInput = $("logsQuery");
  if (logsQueryInput) {
    logsQueryInput.addEventListener("input", () => {
      if (logsQueryTimer) window.clearTimeout(logsQueryTimer);
      logsQueryTimer = window.setTimeout(async () => {
        try {
          hideNotice();
          logsState.query = logsQueryInput.value.trim();
          logsState.page = 1;
          await refreshLogs();
        } catch (err) {
          showNotice(err.message || "搜索失败", "error");
        }
      }, 250);
    });
  }

  let usersQueryTimer = null;
  const usersQueryInput = $("usersQuery");
  if (usersQueryInput) {
    usersQueryInput.addEventListener("input", () => {
      if (usersQueryTimer) window.clearTimeout(usersQueryTimer);
      usersQueryTimer = window.setTimeout(async () => {
        try {
          hideNotice();
          usersState.query = usersQueryInput.value.trim();
          usersState.page = 1;
          await refreshUsers();
        } catch (err) {
          showNotice(err.message || "搜索失败", "error");
        }
      }, 250);
    });
  }

  let adminLogsQueryTimer = null;
  const adminLogsQueryInput = $("adminLogsQuery");
  if (adminLogsQueryInput) {
    adminLogsQueryInput.addEventListener("input", () => {
      if (adminLogsQueryTimer) window.clearTimeout(adminLogsQueryTimer);
      adminLogsQueryTimer = window.setTimeout(async () => {
        try {
          hideNotice();
          adminLogsState.query = adminLogsQueryInput.value.trim();
          adminLogsState.page = 1;
          await refreshAdminLogs();
        } catch (err) {
          showNotice(err.message || "搜索失败", "error");
        }
      }, 250);
    });
  }

  let adminLogsUserIdTimer = null;
  const adminLogsUserIdInput = $("adminLogsUserId");
  if (adminLogsUserIdInput) {
    adminLogsUserIdInput.addEventListener("input", () => {
      if (adminLogsUserIdTimer) window.clearTimeout(adminLogsUserIdTimer);
      adminLogsUserIdTimer = window.setTimeout(async () => {
        try {
          hideNotice();
          adminLogsState.userId = adminLogsUserIdInput.value.trim();
          adminLogsState.page = 1;
          await refreshAdminLogs();
        } catch (err) {
          showNotice(err.message || "搜索失败", "error");
        }
      }, 250);
    });
  }

  if (perPageSelect) {
    perPageSelect.addEventListener("change", async () => {
      try {
        hideNotice();
        accountsState.perPage = Number(perPageSelect.value || 10) || 10;        
        accountsState.page = 1;
        await refreshAccounts();
      } catch (err) {
        showNotice(err.message || "刷新失败", "error");
      }
    });
  }

  if (logsPerPageSelect) {
    logsPerPageSelect.addEventListener("change", async () => {
      try {
        hideNotice();
        logsState.perPage = Number(logsPerPageSelect.value || 20) || 20;
        logsState.page = 1;
        await refreshLogs();
      } catch (err) {
        showNotice(err.message || "刷新失败", "error");
      }
    });
  }

  if (usersPerPageSelect) {
    usersPerPageSelect.addEventListener("change", async () => {
      try {
        hideNotice();
        usersState.perPage = Number(usersPerPageSelect.value || 10) || 10;      
        usersState.page = 1;
        await refreshUsers();
      } catch (err) {
        showNotice(err.message || "刷新失败", "error");
      }
    });
  }

  if (adminLogsPerPageSelect) {
    adminLogsPerPageSelect.addEventListener("change", async () => {
      try {
        hideNotice();
        adminLogsState.perPage = Number(adminLogsPerPageSelect.value || 20) || 20;
        adminLogsState.page = 1;
        await refreshAdminLogs();
      } catch (err) {
        showNotice(err.message || "刷新失败", "error");
      }
    });
  }

  const btnPrev = $("btnPrevPage");
  if (btnPrev) {
    btnPrev.addEventListener("click", async () => {
      try {
        hideNotice();
        accountsState.page = Math.max(1, accountsState.page - 1);
        await refreshAccounts();
      } catch (err) {
        showNotice(err.message || "翻页失败", "error");
      }
    });
  }

  const btnLogsPrev = $("btnLogsPrev");
  if (btnLogsPrev) {
    btnLogsPrev.addEventListener("click", async () => {
      try {
        hideNotice();
        logsState.page = Math.max(1, logsState.page - 1);
        await refreshLogs();
      } catch (err) {
        showNotice(err.message || "翻页失败", "error");
      }
    });
  }

  const btnUsersPrev = $("btnUsersPrev");
  if (btnUsersPrev) {
    btnUsersPrev.addEventListener("click", async () => {
      try {
        hideNotice();
        usersState.page = Math.max(1, usersState.page - 1);
        await refreshUsers();
      } catch (err) {
        showNotice(err.message || "翻页失败", "error");
      }
    });
  }

  const btnAdminLogsPrev = $("btnAdminLogsPrev");
  if (btnAdminLogsPrev) {
    btnAdminLogsPrev.addEventListener("click", async () => {
      try {
        hideNotice();
        adminLogsState.page = Math.max(1, adminLogsState.page - 1);
        await refreshAdminLogs();
      } catch (err) {
        showNotice(err.message || "翻页失败", "error");
      }
    });
  }

  const btnNext = $("btnNextPage");
  if (btnNext) {
    btnNext.addEventListener("click", async () => {
      try {
        hideNotice();
        accountsState.page += 1;
        await refreshAccounts();
      } catch (err) {
        showNotice(err.message || "翻页失败", "error");
      }
    });
  }

  const btnLogsNext = $("btnLogsNext");
  if (btnLogsNext) {
    btnLogsNext.addEventListener("click", async () => {
      try {
        hideNotice();
        logsState.page += 1;
        await refreshLogs();
      } catch (err) {
        showNotice(err.message || "翻页失败", "error");
      }
    });
  }

  const btnUsersNext = $("btnUsersNext");
  if (btnUsersNext) {
    btnUsersNext.addEventListener("click", async () => {
      try {
        hideNotice();
        usersState.page += 1;
        await refreshUsers();
      } catch (err) {
        showNotice(err.message || "翻页失败", "error");
      }
    });
  }

  const btnAdminLogsNext = $("btnAdminLogsNext");
  if (btnAdminLogsNext) {
    btnAdminLogsNext.addEventListener("click", async () => {
      try {
        hideNotice();
        adminLogsState.page += 1;
        await refreshAdminLogs();
      } catch (err) {
        showNotice(err.message || "翻页失败", "error");
      }
    });
  }

  const btnRefreshLogs = $("btnRefreshLogs");
  if (btnRefreshLogs) {
    btnRefreshLogs.addEventListener("click", async () => {
      try {
        hideNotice();
        await refreshLogs();
        showNotice("日志已刷新", "success");
      } catch (err) {
        showNotice(err.message || "刷新失败", "error");
      }
    });
  }

  const btnAdminLogsRefresh = $("btnAdminLogsRefresh");
  if (btnAdminLogsRefresh) {
    btnAdminLogsRefresh.addEventListener("click", async () => {
      try {
        hideNotice();
        await refreshAdminLogs();
        showNotice("全局日志已刷新", "success");
      } catch (err) {
        showNotice(err.message || "刷新失败", "error");
      }
    });
  }

  if (isAppPage) {
    const adminCreateUserForm = $("adminCreateUserForm");
    if (adminCreateUserForm) {
      adminCreateUserForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          hideNotice();
          const username = $("adminNewUsername").value.trim();
          const email = $("adminNewEmail").value.trim();
          const password = $("adminNewPassword").value;
          await api("/api/admin/users", {
            method: "POST",
            body: JSON.stringify({ username, password, email: email || undefined }),
          });
          $("adminNewPassword").value = "";
          usersState.page = 1;
          await refreshUsers();
          await refreshLogs();
          await refreshAdminLogs();
          showNotice("用户已创建", "success");
        } catch (err) {
          showNotice(err.message || "创建失败", "error");
        }
      });
    }

    const adminResetPasswordForm = $("adminResetPasswordForm");
    if (adminResetPasswordForm) {
      adminResetPasswordForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          hideNotice();
          const userId = Number($("adminResetUserId").value);
          const password = $("adminResetPassword").value;
          if (!userId) throw new Error("请填写正确的用户ID");
          await api(`/api/admin/users/${userId}/password`, {
            method: "PUT",
            body: JSON.stringify({ password }),
          });
          $("adminResetPassword").value = "";
          await refreshUsers();
          await refreshLogs();
          await refreshAdminLogs();
          showNotice("密码已重置", "success");
        } catch (err) {
          showNotice(err.message || "重置失败", "error");
        }
      });
    }

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
        if (me.user && me.user.is_admin) {
          usersState.page = 1;
          await refreshUsers();
          adminLogsState.page = 1;
          await refreshAdminLogs();
        }
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
        if (me.user && me.user.is_admin) {
          usersState.page = 1;
          await refreshUsers();
          adminLogsState.page = 1;
          await refreshAdminLogs();
        }
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
        accountsState.page = 1;
        await refreshAccounts();
        showNotice("已刷新", "success");
      } catch (err) {
        showNotice(err.message || "刷新失败", "error");
      }
    });
  }

  // Initial state (shared across pages)
  const token = getToken();
  if (!token) {
    setGuestUI();
    return;
  }

  try {
    const me = await api("/api/user");
    setAuthedUI(me.user);
    if (isAppPage) {
      await refreshAccounts();
      await refreshLogs();
      if (me.user && me.user.is_admin) {
        usersState.page = 1;
        await refreshUsers();
        adminLogsState.page = 1;
        await refreshAdminLogs();
      }
    }
  } catch {
    clearToken();
    setGuestUI();
  }
}

document.addEventListener("DOMContentLoaded", bootstrap);
