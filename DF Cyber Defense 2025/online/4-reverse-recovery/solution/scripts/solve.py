#!/usr/bin/env python3
"""Solver for Pixel Blackout (Reverse Recovery) – end-to-end.

What it does:
- Downloads the required artifacts from hardcoded GitHub RAW commit URLs into an `encrypted/` folder.
- Extracts dynamic key material from `test.png` (fields `k/i/p`).
- Decrypts `sync.dat.enc` and `profile.dat.enc` (AES-CBC + PKCS#5 + Base64) using `k` and `i`.
- Decrypts `bundle.bin.enc` (AES-CBC + PKCS#5) using `MD5(p)` as key and first 16 bytes of `SHA-256(p)` as IV, then inspects the ZIP for `downloads/flag.png`.
- Prints Phase 1/2 results and writes the final concatenated flag to `decrypted/final_flag.txt`.

Usage (no args – uses embedded RAW commit URLs):
  python3 solve_flags.py

Optional: provide your own RAW URLs as args (any order). The script will auto-map by filename.
  python3 solve_flags.py <raw_url1> <raw_url2> ...
"""

from __future__ import annotations

import base64
import io
import json
import re
import sys
import urllib.request
import urllib.parse
import zipfile
from dataclasses import dataclass
from hashlib import md5, sha256
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from Crypto.Cipher import AES  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    sys.stderr.write("[!] PyCryptodome is required: pip install pycryptodome\n")
    raise SystemExit(1) from exc


# Workspace paths
FILES_ROOT = Path(__file__).resolve().parent
ENCRYPTED_ROOT = FILES_ROOT / "encrypted"
DECRYPTED_ROOT = FILES_ROOT / "decrypted"


# Regex to locate the embedded JSON payload inside PNG
PAYLOAD_REGEX = re.compile(r"\{\s*\"k\".*?\}", re.DOTALL)
MASK_VALUE = 0x37  # XOR mask applied to decoded k/i/p bytes


# Default inputs: GitHub RAW commit URLs (hardcoded)
DEFAULT_URLS = [
    "https://raw.githubusercontent.com/centralceeplusplus/wallpapers/71ba6bc3dd108fd16a210a6ee8083550ca1f05c9/test.png",
    "https://raw.githubusercontent.com/centralceeplusplus/wallpapers/8c2a1cec0acc0ba740ef49a59ba199baea633fb5/bundle.bin.enc",
    "https://raw.githubusercontent.com/centralceeplusplus/wallpapers/8c2a1cec0acc0ba740ef49a59ba199baea633fb5/profile.dat.enc",
    "https://raw.githubusercontent.com/centralceeplusplus/wallpapers/8c2a1cec0acc0ba740ef49a59ba199baea633fb5/sync.dat.enc",
]


EXPECTED_NAMES = {"test.png", "bundle.bin.enc", "profile.dat.enc", "sync.dat.enc"}


def ensure_dirs() -> None:
    ENCRYPTED_ROOT.mkdir(parents=True, exist_ok=True)
    DECRYPTED_ROOT.mkdir(parents=True, exist_ok=True)


def pkcs7_unpad(data: bytes) -> bytes:
    if not data:
        return data
    pad = data[-1]
    if pad == 0 or pad > len(data):
        raise ValueError("Invalid PKCS#7 padding")
    if data[-pad:] != bytes([pad]) * pad:
        raise ValueError("Corrupted padding")
    return data[:-pad]


def filename_from_url(url: str) -> str:
    name = Path(urllib.parse.urlparse(url).path).name
    return name


def download(url: str, dest: Path, timeout: float = 20.0) -> None:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; PixelBlackoutSolver/1.0)",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    dest.write_bytes(data)


def fetch_artifacts(urls: List[str]) -> Dict[str, Path]:
    ensure_dirs()
    mapping: Dict[str, Path] = {}
    # Map last path component to URL (so order does not matter)
    for url in urls:
        name = filename_from_url(url)
        if name not in EXPECTED_NAMES:
            # Ignore unrelated inputs
            continue
        path = ENCRYPTED_ROOT / name
        print(f"[*] Downloading {name} …")
        download(url, path)
        size = path.stat().st_size
        print(f"    -> saved {size} bytes to {path}")
        mapping[name] = path
    missing = EXPECTED_NAMES - set(mapping.keys())
    if missing:
        raise RuntimeError(f"Missing expected artifacts after download: {sorted(missing)}")
    return mapping


@dataclass
class KeyMaterial:
    k: bytes  # AES key for C2 strings
    i: bytes  # AES IV for C2 strings
    p: bytes  # password for archive derivation


def extract_material_from_png(png_path: Path) -> KeyMaterial:
    raw_bytes = png_path.read_bytes()
    text = raw_bytes.decode("iso-8859-1", errors="ignore")
    match = PAYLOAD_REGEX.search(text)
    if not match:
        raise ValueError("Payload JSON not found inside PNG")
    payload = json.loads(match.group())
    k = base64.b64decode(payload["k"])  # type: ignore[index]
    i = base64.b64decode(payload["i"])  # type: ignore[index]
    p = base64.b64decode(payload["p"])  # type: ignore[index]
    k = bytes(b ^ MASK_VALUE for b in k)
    i = bytes(b ^ MASK_VALUE for b in i)
    p = bytes(b ^ MASK_VALUE for b in p)
    return KeyMaterial(k=k, i=i, p=p)


def decrypt_secret_cipher_line(line_b64: str, key: bytes, iv: bytes) -> str:
    decoded = base64.b64decode(line_b64)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plain = pkcs7_unpad(cipher.decrypt(decoded))
    return plain.decode("utf-8")


def decrypt_exfil_zip(raw: bytes, password: bytes) -> zipfile.ZipFile:
    key = md5(password).digest()
    iv = sha256(password).digest()[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = pkcs7_unpad(cipher.decrypt(raw))
    return zipfile.ZipFile(io.BytesIO(decrypted))


def recover_phase1(sync_path: Path, key: bytes, iv: bytes) -> List[str]:
    lines = [ln.strip() for ln in sync_path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
    bodies: List[str] = []
    dec_json_lines: List[str] = []
    for ln in lines:
        try:
            dec = decrypt_secret_cipher_line(ln, key, iv)
            dec_json_lines.append(dec)
            obj = json.loads(dec)
            if isinstance(obj, dict):
                bodies.append(str(obj.get("body", "")))
        except Exception as exc:
            print(f"[!] Phase 1 line decrypt failed: {exc}")
    # Save decrypted JSON lines for reference
    (DECRYPTED_ROOT / "sync.decoded.jsonl").write_text(
        "\n".join(dec_json_lines), encoding="utf-8"
    )
    return bodies


def recover_phase2(profile_path: Path, key: bytes, iv: bytes) -> List[Dict[str, str]]:
    payload = profile_path.read_text(encoding="utf-8", errors="ignore").strip()
    try:
        decrypted = decrypt_secret_cipher_line(payload, key, iv)
        # Save raw decrypted profile payload
        (DECRYPTED_ROOT / "profile.decoded.json").write_text(decrypted, encoding="utf-8")
        data = json.loads(decrypted)
        if isinstance(data, list):
            # Normalize to list of dicts with name/number keys if possible
            out: List[Dict[str, str]] = []
            for item in data:
                if isinstance(item, dict):
                    out.append({
                        "name": str(item.get("name", "")),
                        "number": str(item.get("number", "")),
                    })
            return out
    except Exception as exc:
        print(f"[!] Phase 2 decrypt/parse failed: {exc}")
    return []


def recover_phase3(bundle_path: Path, password: bytes) -> List[Tuple[str, bytes]]:
    raw = bundle_path.read_bytes()
    try:
        archive = decrypt_exfil_zip(raw, password)
    except Exception as exc:
        print(f"[!] Phase 3 archive decrypt failed: {exc}")
        return []
    items: List[Tuple[str, bytes]] = []
    with archive:
        for name in archive.namelist():
            with archive.open(name) as fh:
                data = fh.read()
            items.append((name, data))
            # Save extracted file preserving folder structure under decrypted/
            out_path = DECRYPTED_ROOT / name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(data)
    return items


def pick_flag_part1(bodies: Iterable[str]) -> Optional[str]:
    best = None
    for s in bodies:
        t = s.strip()
        if not t:
            continue
        if "DF25{" in t or "flag part 1" in t.lower():
            return t
        best = best or t
    return best


def pick_flag_part2(contacts: Iterable[Dict[str, str]]) -> Optional[str]:
    candidates: List[str] = []
    for c in contacts:
        for field in (c.get("name", ""), c.get("number", "")):
            t = str(field).strip()
            if not t:
                continue
            if "second" in t.lower() or t.count("_") >= 2:
                return t
            candidates.append(t)
    return candidates[0] if candidates else None


def pick_flag_part3(items: Iterable[Tuple[str, bytes]]) -> Optional[str]:
    for name, data in items:
        if name.lower().endswith("flag.png") or name.lower().endswith("flag.txt"):
            text = data.decode("utf-8", errors="ignore").strip()
            if text:
                return text
    # fallback: search any text-like file inside downloads/
    for name, data in items:
        if name.lower().startswith("downloads/"):
            text = data.decode("utf-8", errors="ignore").strip()
            if "flag" in text.lower() or text.endswith("}"):
                return text
    return None


def main(argv: List[str]) -> None:
    # Decide which URLs to use
    input_urls = argv[1:] if len(argv) > 1 else DEFAULT_URLS
    print("[*] Resolving and downloading artifacts…")
    mapping = fetch_artifacts(input_urls)

    # Extract dynamic key material from test.png
    print("[*] Extracting key material from test.png …")
    km = extract_material_from_png(mapping["test.png"])
    k, i, p = km.k, km.i, km.p
    print(f"    k (AES key): {k.decode('utf-8', 'ignore')}")
    print(f"    i (AES IV):  {i.decode('utf-8', 'ignore')}")
    print(f"    p (passwd):  {p.decode('utf-8', 'ignore')}")

    # Phase 1 – keystream
    print("[*] Decrypting Phase 1 (sync.dat.enc) …")
    phase1 = recover_phase1(mapping["sync.dat.enc"], k, i)
    for idx, line in enumerate(phase1, 1):
        print(f"    [{idx}] {line}")
    part1 = pick_flag_part1(phase1)
    if part1:
        print(f"    -> part1: {part1}")
    else:
        print("    -> part1 not found")

    # Phase 2 – contacts
    print("[*] Decrypting Phase 2 (profile.dat.enc) …")
    contacts = recover_phase2(mapping["profile.dat.enc"], k, i)
    for c in contacts:
        print(f"    - {c.get('name', '')}: {c.get('number', '')}")
    part2 = pick_flag_part2(contacts)
    if part2:
        print(f"    -> part2: {part2}")
    else:
        print("    -> part2 not found")

    # Phase 3 – exfil bundle
    print("[*] Decrypting Phase 3 (bundle.bin.enc) …")
    items = recover_phase3(mapping["bundle.bin.enc"], p)
    for name, data in items:
        # Do not print the content of decrypted archive entries (may contain flag.png)
        print(f"    - {name} ({len(data)} bytes)")
    # Determine part3 but DO NOT print it; just note presence
    part3 = pick_flag_part3(items)
    if part3:
        print("    -> part3 recovered (not printed; saved under decrypted/)")
    else:
        print("    -> part3 not found")

    print("\n[*] Encrypted artifacts under", ENCRYPTED_ROOT)
    print("[*] Decrypted outputs under", DECRYPTED_ROOT)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        print("[!] Aborted by user")
