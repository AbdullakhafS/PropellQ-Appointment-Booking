/**
 * PropellQ Shared Utilities — Auth, API client, Toast, Router
 */

// ── Auth ──────────────────────────────────────────────────────────────────
const Auth = {
  TOKEN_KEY: 'pq_token',
  USER_KEY:  'pq_user',

  store(data) {
    sessionStorage.setItem(this.TOKEN_KEY, data.token);
    sessionStorage.setItem(this.USER_KEY, JSON.stringify({
      id:    data.user_id || data.id || '',
      role:  data.role   || 'patient',
      email: data.email  || '',
    }));
  },

  getToken() { return sessionStorage.getItem(this.TOKEN_KEY); },

  getUser() {
    try {
      const u = sessionStorage.getItem(this.USER_KEY);
      return u ? JSON.parse(u) : null;
    } catch { return null; }
  },

  clear() {
    sessionStorage.removeItem(this.TOKEN_KEY);
    sessionStorage.removeItem(this.USER_KEY);
  },

  isLoggedIn() { return !!this.getToken(); },
  getRole()    { const u = this.getUser(); return u ? u.role : null; },

  requireAuth() {
    if (!this.isLoggedIn()) { window.location.href = '/login.html'; return false; }
    return true;
  },

  requireRole(role) {
    if (!this.requireAuth()) return false;
    if (this.getRole() !== role) { this.redirectToPortal(); return false; }
    return true;
  },

  redirectToPortal() {
    const r = this.getRole();
    if (r === 'admin')  { window.location.href = '/admin.html';   return; }
    if (r === 'staff')  { window.location.href = '/staff.html';   return; }
    window.location.href = '/patient.html';
  },

  logout() { this.clear(); window.location.href = '/login.html'; },
};

// ── API Client ────────────────────────────────────────────────────────────
const API = {
  async request(method, path, body) {
    const token = Auth.getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const opts = { method, headers };
    if (body !== undefined) opts.body = JSON.stringify(body);

    try {
      const res = await fetch(path, opts);
      if (res.status === 401) { Auth.logout(); return null; }
      const data = await res.json();
      return { ok: res.ok, status: res.status, data };
    } catch (e) {
      console.error(`API ${method} ${path}:`, e);
      return { ok: false, status: 0, data: null };
    }
  },

  get(path)         { return this.request('GET',   path); },
  post(path, body)  { return this.request('POST',  path, body); },
  put(path, body)   { return this.request('PUT',   path, body); },
  patch(path, body) { return this.request('PATCH', path, body); },

  // multipart (file upload)
  async upload(path, formData) {
    const token = Auth.getToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    try {
      const res = await fetch(path, { method: 'POST', headers, body: formData });
      if (res.status === 401) { Auth.logout(); return null; }
      const data = await res.json();
      return { ok: res.ok, status: res.status, data };
    } catch (e) {
      console.error('Upload error:', e);
      return { ok: false, status: 0, data: null };
    }
  },
};

// ── Toast ─────────────────────────────────────────────────────────────────
const Toast = {
  _ensure() {
    let c = document.getElementById('pq-toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'pq-toast-container';
      c.className = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  },
  show(msg, type = 'success', ms = 3500) {
    const c = this._ensure();
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => {
      t.style.cssText = 'opacity:0;transition:opacity .3s';
      setTimeout(() => t.remove(), 300);
    }, ms);
  },
  success(m) { this.show(m, 'success'); },
  error(m)   { this.show(m, 'error', 5000); },
  warning(m) { this.show(m, 'warning'); },
};

// ── Router (hash-based) ───────────────────────────────────────────────────
const Router = {
  handlers: {},

  on(view, fn) { this.handlers[view] = fn; },

  go(view) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-tab[data-view]').forEach(t => t.classList.remove('active'));
    const el = document.getElementById(`view-${view}`);
    if (el) el.classList.add('active');
    const tab = document.querySelector(`.nav-tab[data-view="${view}"]`);
    if (tab) tab.classList.add('active');
    window.location.hash = view;
    if (this.handlers[view]) this.handlers[view]();
  },

  init(defaultView) {
    document.querySelectorAll('.nav-tab[data-view]').forEach(tab => {
      tab.addEventListener('click', () => this.go(tab.dataset.view));
    });
    const hash = window.location.hash.replace('#', '');
    this.go(hash && document.getElementById(`view-${hash}`) ? hash : defaultView);
  },
};

// ── Nav helper ────────────────────────────────────────────────────────────
function initNav() {
  const user = Auth.getUser();
  if (!user) return;
  const el = id => document.getElementById(id);
  if (el('navUserId'))   el('navUserId').textContent   = user.id;
  if (el('navUserAvatar')) el('navUserAvatar').textContent = (user.id || 'U')[0].toUpperCase();
  if (el('navUserRole')) {
    el('navUserRole').textContent = user.role;
    el('navUserRole').className   = `badge badge-${
      user.role === 'admin' ? 'error' : user.role === 'staff' ? 'warning' : 'primary'
    }`;
  }
}

// ── Formatters ────────────────────────────────────────────────────────────
function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function fmtTime(t) {
  if (!t) return '';
  const [h, m] = t.split(':');
  const hr = parseInt(h, 10);
  return `${hr % 12 || 12}:${m} ${hr >= 12 ? 'PM' : 'AM'}`;
}
function fmtDateTime(d) {
  if (!d) return '—';
  return new Date(d).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}
function statusBadge(status) {
  const map = {
    available: 'primary', booked: 'success', cancelled: 'error',
    confirmed: 'success', reserved: 'warning', searching: 'neutral',
    active: 'success', inactive: 'neutral', suspended: 'error',
    pending: 'warning', synced: 'success', failed: 'error',
    checked_in: 'info', waiting: 'warning', in_room: 'success', completed: 'neutral',
    open: 'warning', resolved: 'success',
  };
  const cls = map[status] || 'neutral';
  return `<span class="badge badge-${cls}">${status.replace(/_/g, ' ')}</span>`;
}

// ── Inner tab switcher ────────────────────────────────────────────────────
function initInnerTabs(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.querySelectorAll('.inner-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      container.querySelectorAll('.inner-tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.inner-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const panel = container.querySelector(`#${tab.dataset.panel}`);
      if (panel) panel.classList.add('active');
    });
  });
  const first = container.querySelector('.inner-tab');
  if (first) first.click();
}

// ── Alert helpers ─────────────────────────────────────────────────────────
function showAlert(id, msg, type = 'error') {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  el.classList.remove('hidden');
}
function hideAlert(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}

// ── Confirm dialog ────────────────────────────────────────────────────────
function pqConfirm(message) {
  return window.confirm(message);
}

// ── Build query string ────────────────────────────────────────────────────
function buildQuery(params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== '' && v != null) q.set(k, v); });
  const s = q.toString();
  return s ? `?${s}` : '';
}
