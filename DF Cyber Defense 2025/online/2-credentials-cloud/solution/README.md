# Time Is Gold - Solution

## Writeups from the teams
- [Team CIMB](https://github.com/danh-software/DF25_Online_Round/blob/main/Gold.md)
- [Team TPBank](https://minhnb11.notion.site/CTF-Time-is-gold-277b0fe6422780308ceffc1343459e87)
- [Team MBBank](https://anhdq201.wordpress.com/2025/09/24/write-up-cyber-defense-2025-time-is-gold/)

## TL;DR
- This challenge is inspired from [CVE-2024-34273](https://github.com/advisories/GHSA-3hvj-2783-34x2), and the idea to pollute `baseURL` in Axios to turn into SSRF.
- Use the [nginx alias path traversal bug](https://www.facebook.com/share/p/17BkHQD2pY/) to fetch `/server.js` with `GET /assets../server.js` and read the backend code.
- Forge a JWT header with `typ: "__proto__"` and `reservedKeys: []` so the server accepts our unsigned token and shows the admin panel, which leaks S3 image URL.
- Use the same prototype pollution to inject `baseURL` into the Axios client, turning the `/api/gold` endpoint into an SSRF tool that can reach AWS metadata.
- Query metadata to learn the IAM role name, grab the temporary AWS keys, then list `s3://gold-price-ctf-prod/` and read the flag file.

## Attack Walkthrough

### 1. Leak the server file
The site serves static files from `alias /app/src/static/` without cleaning up `..`. Hitting `/assets../server.js` returns the Node.js source, which shows the custom JWT handler and the gold price proxy.

### 2. Make an admin token
`jwtVerify` copies header fields into a shared store and skips protections for `__proto__`. Setting `typ` to `"__proto__"` plus `reservedKeys: []` clears the required header list, so signature checks never run. We pick any payload we like, set `admin: true`, and call `/api/admin/config` to read the page that exposes the S3 image path.

### 3. Rewrite Axios defaults
We keep the same polluted header and also add `baseURL: "http://169.254.169.254"`. When we request `/api/gold?index=6m&direct=false`, the shared Axios client inherits our base URL and follows our path, so the backend now sends requests to the AWS metadata service.

Note: when polluting the `baseURL`, we need to append a "?" at the end (e.g., `http://169.254.169.254/latest/meta-data/iam/security-credentials/${roleName}?`) to properly handle URL concatenation in Axios.

### 4. Pull AWS creds and loot S3
First request `/latest/meta-data/iam/security-credentials/` to get the role name, then fetch the JSON keys for that role. Export them and run `aws s3 ls s3://gold-price-ctf-prod/ --recursive` and `aws s3 cp s3://gold-price-ctf-prod/flags/flag.txt ./flag.txt` to download the flag.

## Flag
`DF25{Cloud9HackingTo5_w1th_prototyping}`

## References
- [`exploit.js`](exploit.js): automation script for the whole leak → metadata → S3 chain.
- Doyensec – [Server-side Prototype Pollution Gadget Scanner](https://blog.doyensec.com/2024/02/17/server-side-prototype-pollution-Gadgets-scanner.html)
- [CVE-2024-34273](https://github.com/advisories/GHSA-3hvj-2783-34x2)
