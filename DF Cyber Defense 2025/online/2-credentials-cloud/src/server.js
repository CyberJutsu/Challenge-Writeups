import http from 'http';
import https from 'https';
import url from 'url';
import crypto from 'crypto';
import axios from 'axios';
import { encode as jwtEncode, verify as jwtVerify } from './jwt.js';
import { cleanup, USERS } from '../lib/utils.js';

const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || crypto.randomBytes(32);
const GOLD_IMG_URL = process.env.S3_GOLD_URL || '';
const GOLD_API_PATH = '/du-lieu/Ajax/ajaxgoldpricehistory.ashx';
const DEFAULT_GOLD_BASE_URL = 'https://cafef.vn';
const DEFAULT_PROFILE = Object.freeze({
  locale: 'vi-VN',
  preferences: { goldRange: '6m' },
  http: {
    headers: {
      'User-Agent': 'GoldPriceClient/1.0',
    },
  },
});

const goldHttpClient = axios.create({
  timeout: 8000,
  maxRedirects: 0,
  httpAgent: new http.Agent({ keepAlive: true }),
  httpsAgent: new https.Agent({ keepAlive: true }),
  headers: {
    'User-Agent': 'GoldPriceClient/1.0',
  },
});

const json = (res, status, data, extraHeaders = {}) => {
  const body = JSON.stringify(data);
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Content-Length', Buffer.byteLength(body));
  for (const [key, value] of Object.entries(extraHeaders || {})) {
    if (typeof value !== 'undefined') res.setHeader(key, value);
  }
  res.end(body);
};
const parseBody = (req) => new Promise((resolve, reject) => {
  let data = '';
  req.on('data', (c) => { data += c; if (data.length > 1e6) { req.destroy(); reject(new Error('Body too large')); } });
  req.on('end', () => { if (!data) return resolve({}); try { resolve(JSON.parse(data)); } catch { reject(new Error('Invalid JSON')); } });
});
const bearer = (req) => {
  const h = req.headers['authorization'] || req.headers['Authorization'];
  const m = h && /\s*Bearer\s+([^\s]+)/i.exec(h);
  return m ? m[1] : null;
};

const escapeHtml = (value) => String(value || '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;');



// buildDecoyIntel function removed

function renderAdminPanel(username, goldImageUrl) {
  const displayName = escapeHtml(username || 'admin');
  const safeUrl = goldImageUrl ? escapeHtml(goldImageUrl) : '';
  const imageBlock = safeUrl
    ? `<img src="${safeUrl}" alt="Gold asset" />`
    : '<span class="muted">Chưa cấu hình GOLD_IMG_URL.</span>';
  
  return `
    <div class="admin-panel">
      <div class="panel-header">Xin chào ${displayName}</div>
      <div class="panel-body">
        ${imageBlock} Chức năng điều chỉnh theme đã bị khóa.
        <!-- <a href="/edit-theme">Chỉnh sửa theme</a> -->
      </div>
    </div>
  `.trim();
}

const htmlIndex = (user = {}) => {
  const displayName = escapeHtml(user && user.username ? user.username : 'guest');
  const adminAttr = user && user.admin === true ? '1' : '0';
  return `<!doctype html>
<html lang="vi">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Live Giá Vàng</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Arial, sans-serif; margin: 2rem auto; max-width: 1000px; padding: 0 1rem; background: #fff; color: #222; }
      header { display: flex; align-items: center; gap: 1.5rem; justify-content: space-between; }
      .branding { display: flex; flex-direction: column; gap: 0.25rem; }
      h1 { margin: 0; font-size: 1.5rem; }
      .tagline { font-size: 0.9rem; }
      .header-right { display: flex; flex-direction: column; align-items: flex-end; gap: 0.35rem; }
      .welcome { font-size: 0.95rem; font-weight: 500; color: #213665; }
      .welcome .admin-user { color: #d6336c; }
      .range-select { display: flex; align-items: center; gap: 0.5rem; }
      .muted { color: #555; }
      .grid { display: grid; grid-template-columns: 320px 1fr; gap: 1rem; margin-top: 1rem; }
      .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; background: #fff; }
      .title { font-weight: 600; margin-bottom: 0.5rem; }
      .big { font-size: 1.8rem; font-weight: 700; }
      .row { display: flex; justify-content: space-between; margin: 0.35rem 0; }
      .pill { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.8rem; background: #eef; color: #334; border: 1px solid #dde; }
      .chart-card { height: 420px; overflow: hidden; }
      .chart-card canvas { display: block; width: 100% !important; height: 100% !important; }
      table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
      th, td { border-bottom: 1px solid #eee; padding: 0.5rem; text-align: left; font-size: 0.95rem; }
      select { padding: 0.5rem; border-radius: 8px; border: 1px solid #ddd; background: #fff; color: #222; }
      code { background: #f6f8fa; padding: 0.15rem 0.3rem; border-radius: 4px; }
      footer { margin-top: 1rem; color: #666; font-size: 0.9rem; }
      form { display: flex; flex-direction: column; gap: 0.5rem; }
      input[type="text"], input[type="password"], button { padding: 0.55rem 0.75rem; border: 1px solid #ccc; border-radius: 6px; font-size: 0.95rem; }
      button { cursor: pointer; background: #0b5ed7; color: #fff; border-color: #0a53be; transition: background 0.15s ease; }
      button:hover { background: #0949ab; }
      #adminPanel { display: none; }
      .admin-panel { display: flex; flex-direction: column; gap: 0.75rem; }
      .admin-panel img { max-height: 120px; border-radius: 8px; box-shadow: 0 4px 14px rgba(0,0,0,0.15); }
      .admin-panel .panel-header { font-weight: 600; font-size: 1.05rem; }
      .admin-panel .panel-body { display: flex; flex-direction: column; gap: 0.5rem; }
      .admin-panel .panel-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.75rem; }
      .admin-panel section { border: 1px solid #dce1ff; background: #f8faff; padding: 0.75rem; border-radius: 8px; }
      .admin-panel h2 { margin: 0 0 0.4rem 0; font-size: 1rem; font-weight: 600; color: #213665; }
      .admin-panel ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.35rem; }
      .admin-panel li { display: flex; flex-direction: column; gap: 0.2rem; padding: 0.45rem 0.5rem; border-radius: 6px; background: rgba(33, 54, 101, 0.07); }
      .admin-panel li code { font-family: 'SFMono-Regular', Menlo, Consolas, monospace; font-size: 0.78rem; }
      .admin-panel details { background: rgba(33, 54, 101, 0.04); padding: 0.65rem; border-radius: 6px; }
      .admin-panel details summary { cursor: pointer; font-weight: 600; }
      .status-success { color: #198754; }
      .status-error { color: #d6336c; }
    </style>
  </head>
  <body>
    <header>
      <div class="branding">
        <h1>Giá vàng</h1><span style="color: #999; font-size: 0.6em; font-weight: normal;">v1.0</span>
      </div>
      <div class="header-right">
        <div class="welcome">Chào mừng <span id="welcomeName" data-user="${displayName}" data-admin="${adminAttr}">${displayName}</span>!</div>
        <div class="range-select">
          <label class="muted" for="range">Kỳ thời gian</label>
          <select id="range">
            <option value="1w">1 Tuần</option>
            <option value="2w">2 Tuần</option>
            <option value="1m">1 Tháng</option>
            <option value="3m">3 Tháng</option>
            <option value="6m" selected>6 Tháng</option>
            <option value="1y">1 Năm</option>
            <option value="all">Tất cả</option>
          </select>
        </div>
      </div>
    </header>

    <section class="grid">
      <div class="card">
        <div class="title">Giá vàng miếng SJC</div>
        <div class="row"><span class="muted">Mua vào</span> <span id="buy" class="big">—</span></div>
        <div class="row"><span class="muted">Bán ra</span> <span id="sell" class="big">—</span></div>
        <div class="row"><span class="muted">Cập nhật</span> <span id="updated" class="pill">—</span></div>
        <div class="muted" style="margin-top: .25rem">Đơn vị: triệu đồng / lượng</div>
      </div>
      <div class="card chart-card">
        <div class="title">Diễn biến giá vàng miếng SJC</div>
        <canvas id="chart" height="320"></canvas>
      </div>
    </section>

    <section class="card" style="margin-top:1rem">
      <table>
        <thead><tr><th>Loại vàng</th><th>Giá mua</th><th>Giá bán</th></tr></thead>
        <tbody id="tableBody"><tr><td class="muted">Đang tải…</td><td></td><td></td></tr></tbody>
      </table>
    </section>
    <footer style="text-align: right;">Powered by Finova.One</footer>
    <div id="loginStatus" class="muted" style="display: none;"></div>
    <section class="card" id="adminPanel" style="margin-top:1rem"></section>
    <script src="/assets/app.js"></script>
  </body>
 </html>`;
};

function sendIndex(req, res) {
  const html = htmlIndex();
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Content-Length', Buffer.byteLength(html));
  res.end(html);
}

async function handleLogin(req, res) {
  try {
    const body = await parseBody(req);
    const user = USERS.get(String(body.username || ''));
    if (!user || user.password !== String(body.password || '')) return json(res, 401, { error: 'invalid credentials' });
    const token = mintToken(user, { expiresIn: 900 });
    return json(res, 200, { token, user: { username: user.username, admin: !!user.admin } });
  } catch (e) {
    return json(res, 400, { error: e.message || 'bad request' });
  }
}

function verifyTokenFromRequest(req, res) {
  const tok = bearer(req);
  if (!tok) {
    json(res, 401, { error: 'missing bearer token' });
    return null;
  }
  try {
    const policyStore = {};
    const { header, body } = jwtVerify(tok, JWT_SECRET, { policyStore });
    return { header, body, policyStore };
  } catch {
    json(res, 401, { error: 'invalid token' });
    return null;
  }
}

function requireAdmin(auth, res) {
  if (!auth || !auth.body || auth.body.admin !== true) {
    json(res, 403, { error: 'admin required' });
    return false;
  }
  return true;
}

function handleMe(req, res) {
  const auth = verifyTokenFromRequest(req, res);
  if (!auth) return;
  return json(res, 200, { user: auth.body });
}

function handleAdminConfig(req, res) {
  const auth = verifyTokenFromRequest(req, res);
  if (!auth) return;
  if (!requireAdmin(auth, res)) return;
  const panelHtml = renderAdminPanel(auth.body && auth.body.username, GOLD_IMG_URL);
  return json(res, 200, { goldImageUrl: GOLD_IMG_URL, panelHtml });
}

async function handleGold(req, res) {
  try {
    const auth = verifyTokenFromRequest(req, res);
    if (!auth) return;
    const { query } = url.parse(req.url, true);
    const profile = {
      locale: DEFAULT_PROFILE.locale,
      preferences: { ...(DEFAULT_PROFILE.preferences || {}) },
      http: {
        headers: { ...((DEFAULT_PROFILE.http && DEFAULT_PROFILE.http.headers) || {}) },
      },
    };
    const allowed = new Set(['1w', '2w', '1m', '3m', '6m', '1y', 'all']);
    let idx = '6m';
    const requestedIdx = String(query.index || '').toLowerCase();
    if (requestedIdx && allowed.has(requestedIdx)) {
      idx = requestedIdx;
    } else {
      const preferred = profile && profile.preferences && typeof profile.preferences.goldRange === 'string'
        ? profile.preferences.goldRange.toLowerCase()
        : '';
      if (preferred && allowed.has(preferred)) idx = preferred;
    }
    const requestConfig = {
      params: { index: idx },
      responseType: 'text',
      headers: {},
    };
    for (const headerName in profile.http.headers) {
      requestConfig.headers[headerName] = profile.http.headers[headerName];
    }
    const directFetch = query.direct !== 'false' && query.direct !== '0';

    let response;
    if (directFetch) {
      const absoluteUrl = new url.URL(GOLD_API_PATH, DEFAULT_GOLD_BASE_URL).toString();
      const directConfig = {
        ...requestConfig,
        headers: { ...(requestConfig.headers || {}) },
        timeout: goldHttpClient.defaults.timeout,
        maxRedirects: goldHttpClient.defaults.maxRedirects,
        httpAgent: goldHttpClient.defaults.httpAgent,
        httpsAgent: goldHttpClient.defaults.httpsAgent,
        validateStatus: goldHttpClient.defaults.validateStatus,
      };
      response = await axios.get(absoluteUrl, directConfig);
    } else {
      console.log('[+] using goldHttpClient:', goldHttpClient.defaults.baseURL);
      response = await goldHttpClient.get(GOLD_API_PATH, requestConfig);
    }
    const payload = response.data;
    if (typeof payload === 'string') {
      try {
        return json(res, 200, JSON.parse(payload));
      } catch {
        return json(res, 200, { raw: payload });
      }
    }
    return json(res, 200, payload);
  } catch (e) {
    return json(res, 502, { error: e.message || 'fetch failed' });
  } finally {
    cleanup();
  }
}

const mintToken = (user, { expiresIn = 300 } = {}) => {
  const now = Math.floor(Date.now() / 1000);
  const ttl = Number.isFinite(expiresIn) && expiresIn > 0 ? Math.floor(expiresIn) : 300;
  return jwtEncode({ sub: user.id, username: user.username, admin: !!user.admin, iat: now, exp: now + ttl, jti: crypto.randomUUID() }, JWT_SECRET, { typ: 'JWT', alg: 'HS256' });
};

async function handleGuestToken(req, res) {
  try {
    const guestUser = USERS.get('guest');
    if (!guestUser) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Guest user not found' }));
      return;
    }

    const token = mintToken(guestUser);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ 
      token, 
      user: { 
        username: guestUser.username, 
        admin: guestUser.admin 
      } 
    }));
  } catch (error) {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Failed to generate guest token' }));
  }
}

async function handler(req, res) {
  const { pathname } = url.parse(req.url, true);

  if (req.method === 'GET' && pathname === '/') return sendIndex(req, res);
  if (req.method === 'GET' && pathname === '/api/guest-token') return handleGuestToken(req, res);
  if (req.method === 'POST' && pathname === '/api/login') return handleLogin(req, res);
  if (req.method === 'GET' && pathname === '/api/me') return handleMe(req, res);
  if (req.method === 'GET' && pathname === '/api/admin/config') return handleAdminConfig(req, res);
  if (req.method === 'GET' && pathname === '/api/gold') return handleGold(req, res);

  res.writeHead(404); res.end();
}

http.createServer(handler).listen(PORT);
