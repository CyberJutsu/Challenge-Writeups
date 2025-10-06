export function b64urlEncode(buf) {
  const b64 = Buffer.from(buf).toString('base64');
  return b64.replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
}

export function b64urlDecode(str) {
  const pad = 4 - (str.length % 4 || 4);
  const b64 = str.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat(pad % 4);
  return Buffer.from(b64, 'base64');
}

