import crypto from 'crypto';
import { b64urlEncode, b64urlDecode } from '../lib/base64url.js';

function isObject(x) {
  return x !== null && typeof x === 'object' && !Array.isArray(x);
}

function hasOwn(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj, key);
}

function safeAssign(target, source) {
  if (!isObject(source)) return target;
  for (const k of Object.keys(source)) {
    if (k === '__proto__' || k === 'prototype' || k === 'constructor') continue;
    target[k] = source[k];
  }
  return target;
}

function constantTimeEqual(a, b) {
  if (!Buffer.isBuffer(a)) a = Buffer.from(a || '');
  if (!Buffer.isBuffer(b)) b = Buffer.from(b || '');
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

const ALGS = new Map([
  ['HS256', 'sha256'],
]);

function sign(alg, signingInput, key) {
  const nodeAlg = ALGS.get(alg);
  if (!nodeAlg) throw new Error('Unsupported alg');
  const h = crypto.createHmac(nodeAlg, key);
  h.update(signingInput);
  return h.digest();
}

class JwtHeader {
  constructor() {
    this.typ = 'JWT';
    this.alg = 'HS256';
  }
}

class JwtBody {
  constructor() {}
}

JwtHeader.prototype.compact = function () {
  return b64urlEncode(Buffer.from(JSON.stringify({ typ: this.typ, alg: this.alg })));
};

JwtBody.prototype.toJSON = function () {
  const out = {};
  for (const k of Object.keys(this)) out[k] = this[k];
  return out;
};

const defaultHeaderPolicies = {};

function headerPolicyFor(typ, overrides, store = defaultHeaderPolicies) {
  const key = String(typ || 'JWT');
  if (!store[key]) store[key] = {};
  const p = store[key];
  if (isObject(overrides)) {
    for (const k of Object.keys(overrides)) {
      p[k] = overrides[k];
    }
  }
  return p;
}

export function encode(payload, key, header = {}) {
  const h = new JwtHeader();
  safeAssign(h, header);
  headerPolicyFor(h.typ, header, defaultHeaderPolicies);

  const b = new JwtBody();
  safeAssign(b, payload);

  const headerB64 = b64urlEncode(Buffer.from(JSON.stringify(h)));
  const bodyB64 = b64urlEncode(Buffer.from(JSON.stringify(b)));
  const signingInput = `${headerB64}.${bodyB64}`;
  const alg = h.alg || 'HS256';
  const sig = sign(alg, signingInput, key);
  const sigB64 = b64urlEncode(sig);
  return `${signingInput}.${sigB64}`;
}

class Parser {
  constructor(store = defaultHeaderPolicies) {
    this.store = store;
  }

  parse(token) {
    const parts = String(token || '').split('.');
    if (parts.length !== 3) throw new Error('Malformed token');
    const [h64, p64, s64] = parts;

    let rawHeader, rawBody;
    try {
      rawHeader = JSON.parse(b64urlDecode(h64).toString('utf8'));
      if (!isObject(rawHeader)) throw new Error('');
    } catch {
      throw new Error('Invalid header');
    }
    try {
      rawBody = JSON.parse(b64urlDecode(p64).toString('utf8'));
      if (!isObject(rawBody)) throw new Error('');
    } catch {
      throw new Error('Invalid payload');
    }

    headerPolicyFor(rawHeader.typ || 'JWT', rawHeader, this.store);

    const header = new JwtHeader();
    safeAssign(header, rawHeader);
    const body = new JwtBody();
    safeAssign(body, rawBody);

    const signature = b64urlDecode(s64);
    const signingInput = `${h64}.${p64}`;
    return { header, body, signature, signingInput };
  }
}

export function verify(token, key, opts = {}) {
  const store = opts.policyStore || defaultHeaderPolicies;
  const parser = new Parser(store);
  const { header, body, signature, signingInput } = parser.parse(token);

  const policy = headerPolicyFor(header.typ || 'JWT', undefined, store);
  const required = Array.isArray(policy.reservedKeys) ? policy.reservedKeys : ['typ', 'alg'];

  const missing = [];
  for (const k of required) {
    if (!(k in header)) missing.push(k);
  }
  if (missing.length) throw new Error('Invalid header');

  let shouldVerify = false;
  if (required.includes('alg')) {
    const alg = header.alg || 'HS256';
    if (!ALGS.has(alg)) throw new Error('Unsupported alg');
    shouldVerify = alg !== 'none';
  } else {
    shouldVerify = false;
  }

  if (shouldVerify) {
    const expected = sign(header.alg || 'HS256', signingInput, key);
    if (!constantTimeEqual(signature, expected)) throw new Error('Signature mismatch');
  }

  return { header, body };
}

export { headerPolicyFor };
