import math
import os
import json
import sqlite3
import logging
import time
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

import jwt
from flask import Flask, request, jsonify, Response, make_response, redirect, url_for
from dotenv import load_dotenv
try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

# Ensure environment is loaded before importing the redactor
load_dotenv()
from ai_filter import redactor

DB_PATH = Path(os.getenv("DB_PATH", "db.sqlite3"))
TEAM_TOKENS_PATH = Path(os.getenv("TEAM_TOKENS_PATH", "team_tokens.json"))
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "86400"))
JWT_ISSUER = os.getenv("JWT_ISSUER", "ai-fraud-challenge")
JWT_COOKIE_NAME = os.getenv("JWT_COOKIE_NAME", "team_session")
JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "600"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "50"))
RATE_LIMIT_MIN_INTERVAL = float(os.getenv("RATE_LIMIT_MIN_INTERVAL", "3"))
FLAG_VALUE = os.getenv("FLAG")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(seed: bool = True) -> None:
    if DB_PATH.exists():
        return
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    conn.commit()
    conn.close()


def load_team_tokens(path: Path) -> Dict[str, Dict[str, Any]]:
    tokens: Dict[str, Dict[str, Any]] = {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        logging.getLogger(__name__).warning("Team token file not found at %s", path)
        return tokens
    except json.JSONDecodeError:
        logging.getLogger(__name__).exception("Team token file is not valid JSON: %s", path)
        return tokens
    except Exception:
        logging.getLogger(__name__).exception("Failed to load team tokens from %s", path)
        return tokens

    if not isinstance(raw, list):
        logging.getLogger(__name__).warning("Team token file %s does not contain a list", path)
        return tokens

    for entry in raw:
        if not isinstance(entry, dict):
            continue
        token_value = (entry.get("token") or "").strip()
        if not token_value:
            continue
        tokens[token_value] = entry
    return tokens


def issue_session_jwt(team_entry: Dict[str, Any]) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not configured")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": team_entry.get("token"),
        "team_abbr": team_entry.get("abbr"),
        "team_full_name": team_entry.get("full_name"),
        "iss": JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=JWT_EXP_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


app = Flask(__name__)

# Configure logging for the Flask app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [FLASK] %(message)s'
)
logger = logging.getLogger(__name__)

if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(32)
    logger.warning(
        "JWT_SECRET not set; generated ephemeral secret. Sessions will reset on restart. Configure JWT_SECRET env for persistence."
    )

TEAM_TOKEN_MAP = load_team_tokens(TEAM_TOKENS_PATH)
if not TEAM_TOKEN_MAP:
    logger.warning("No team tokens loaded from %s", TEAM_TOKENS_PATH)

UNPROTECTED_PREFIXES = ("/auth", "/health", "/hint", "/static")
REDACTED_PREFIXES = ("/users", "/search", "/export")
RATE_LIMIT_STATE: Dict[str, Dict[str, Any]] = {}
RATE_LIMIT_LOCK = Lock()
REDIS_URL = os.getenv("REDIS_URL")
REDIS_PREFIX = os.getenv("REDIS_PREFIX", "aifraud")
_REDIS_CLIENT = None


def get_redis_client():
    global _REDIS_CLIENT
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT
    if not REDIS_URL or redis is None:
        return None
    try:
        _REDIS_CLIENT = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        # Test connection
        _REDIS_CLIENT.ping()
        logger.info("Connected Redis for rate limiting at %s", REDIS_URL)
        return _REDIS_CLIENT
    except Exception:
        logger.exception("Redis unavailable; falling back to in-memory rate limiting")
        _REDIS_CLIENT = None
        return None


@app.after_request
def ai_redact_response(response: Response):
    """Intercept outgoing responses and pass through AI redactor.

    For the challenge, we redact for JSON and text responses.
    """
    path = request.path or ""
    # Do not run AI redaction for non-200 responses to avoid unnecessary API calls
    # (e.g., 401/403/429 should short-circuit without invoking the AI filter).
    if response.status_code != 200:
        return response
    # Skip healthz, auth, static, and non-protected paths
    if (
        path.startswith("/health")
        or path.startswith("/static")
        or path.startswith("/auth")
        or not any(path.startswith(prefix) for prefix in REDACTED_PREFIXES)
    ):
        return response

    content_type = (response.mimetype or "").lower()
    if content_type in {"application/json", "text/plain", "text/html"}:
        try:
            # Read as text, send to AI, then set back
            body = response.get_data(as_text=True)
            redacted = redactor.redact_text(body, content_type=content_type)
            response.set_data(redacted)
        except Exception:
            app.logger.exception("AI redaction failed for %s", path)
            if content_type == "application/json":
                failure_body = json.dumps({"error": "ai_redaction_failed"})
                return Response(failure_body, status=503, mimetype="application/json")
            failure_body = "AI redaction failed"
            failure_type = content_type if content_type in {"text/plain", "text/html"} else "text/plain"
            return Response(failure_body, status=503, mimetype=failure_type)
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/hint")
def hint():
    """Return only the system prompt as plain text."""
    try:
        sp = getattr(redactor, "system_prompt", "") or ""
        return Response(sp, mimetype="text/plain")
    except Exception:
        logger.exception("Failed to render /hint")
        return Response("unavailable", mimetype="text/plain", status=500)


@app.route("/auth", methods=["GET", "POST"])
def authenticate_team():
    if request.method == "GET":
        return render_auth_page()

    token_value = ""
    if request.is_json:
        body = request.get_json(silent=True) or {}
        token_value = (body.get("token") or "").strip()

    if not token_value:
        token_value = (request.form.get("token") or "").strip()

    if not token_value:
        token_value = (request.values.get("token") or "").strip()

    is_form_post = request.mimetype in {"application/x-www-form-urlencoded", "multipart/form-data"}

    if not token_value:
        if is_form_post:
            return render_auth_page("Vui lòng nhập team token.", status_code=400)
        return jsonify({"error": "missing_token"}), 400

    team_entry = TEAM_TOKEN_MAP.get(token_value)
    if not team_entry:
        if is_form_post:
            return render_auth_page("Token không hợp lệ.", status_code=401)
        return jsonify({"error": "invalid_token"}), 401

    try:
        encoded = issue_session_jwt(team_entry)
    except RuntimeError:
        logger.exception("Cannot issue JWT because JWT_SECRET is missing")
        if is_form_post:
            return render_auth_page("Máy chủ chưa cấu hình JWT_SECRET.", status_code=500)
        return jsonify({"error": "server_misconfigured"}), 500

    logger.info("Issued session JWT for team %s", team_entry.get("abbr"))

    if is_form_post:
        resp = redirect(url_for("index"))
    else:
        payload = {
            "team": {
                "abbr": team_entry.get("abbr"),
                "full_name": team_entry.get("full_name"),
            },
            "jwt": encoded,
            "expires_in": JWT_EXP_SECONDS,
        }
        resp = make_response(jsonify(payload))

    resp.set_cookie(
        JWT_COOKIE_NAME,
        encoded,
        httponly=True,
        secure=JWT_COOKIE_SECURE,
        samesite="Lax",
        max_age=JWT_EXP_SECONDS,
    )

    if is_form_post:
        return resp

    return resp


@app.before_request
def require_authentication():
    path = request.path or ""

    if any(path.startswith(prefix) for prefix in UNPROTECTED_PREFIXES):
        return None

    if request.endpoint == "static":
        return None

    if request.method == "OPTIONS":
        return None

    token = extract_session_token()
    if not token:
        return make_unauthorized_response("missing_jwt")

    try:
        claims = decode_session_jwt(token)
    except jwt.ExpiredSignatureError:
        return make_unauthorized_response("token_expired")
    except jwt.InvalidIssuerError:
        return make_unauthorized_response("invalid_token")
    except jwt.InvalidTokenError:
        return make_unauthorized_response("invalid_token")

    team_token = claims.get("sub")
    if not team_token or team_token not in TEAM_TOKEN_MAP:
        return make_unauthorized_response("unknown_team")

    rate_limit_error = enforce_rate_limit(team_token)
    if rate_limit_error is not None:
        return rate_limit_error

    return None


@app.get("/")
def index():
    return render_index_page()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def render_auth_page(message: Optional[str] = None, status_code: int = 200) -> Response:
    message_text = message or ""
    stylesheet = url_for("static", filename="css/style.css")
    html = f"""
<!doctype html>
<html lang=\"vi\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>CTF AI Fraud Access</title>
    <link rel=\"stylesheet\" href=\"{stylesheet}\" />
  </head>
  <body>
    <main>
      <header>
        <div class=\"branding\">
          <h1>AI Fraud Challenge</h1>
          <span class=\"tagline\">Nhập team token để kích hoạt phiên chơi</span>
        </div>
      </header>
      <section class=\"card\">
        <form method=\"post\" autocomplete=\"off\">
          <label for=\"token\">Team token</label>
          <input id=\"token\" name=\"token\" type=\"password\" placeholder=\"VD: TEAM-123abc456\" required autofocus>
          <p class=\"message\">{message_text}</p>
          <button type=\"submit\">Bắt đầu phiên</button>
        </form>
      </section>
      <footer>© 2025 CTF Banking Summit</footer>
    </main>
  </body>
</html>
"""
    return Response(html, mimetype="text/html", status=status_code)


def render_index_page() -> Response:
    stylesheet = url_for("static", filename="css/style.css")
    html = f"""
<!doctype html>
<html lang="vi">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CTF AI Fraud Challenge</title>
    <link rel="stylesheet" href="{stylesheet}" />
  </head>
  <body>
    <main>
      <header>
        <div class="branding">
          <h1>AI Fraud Challenge</h1>
          <span class="tagline">CTF Banking Summit 2025</span>
        </div>
      </header>
      <section class="card">
        <div style="padding: 0.8rem; background: #fff3cd; border-radius: 6px; border-left: 3px solid #ffc107; margin-bottom: 1rem;">
          <strong style="color: #856404;">Hint:</strong>
          <span style="font-size: 0.95rem; color: #555;">Tất cả output HTTP sẽ được đi qua hệ thống AI filtering và dữ liệu nhạy cảm sẽ bị redact thành <code>********</code>.</span>
        </div>
        <h2 style="margin-top: 0; margin-bottom: 1rem; font-size: 1.2rem; color: #333;">Available Endpoints</h2>
        <div style="display: flex; flex-direction: column; gap: 0.8rem;">
          <div style="padding: 0.8rem; background: #f8f9fa; border-radius: 6px; border-left: 3px solid #0b5ed7;">
            <strong style="color: #0b5ed7;">GET /users/&lt;id&gt;</strong>
            <div style="font-size: 0.9rem; color: #666; margin-top: 0.3rem;">Retrieve user information by ID</div>
          </div>
          <div style="padding: 0.8rem; background: #f8f9fa; border-radius: 6px; border-left: 3px solid #0b5ed7;">
            <strong style="color: #0b5ed7;">GET /search?q=&lt;term&gt;</strong>
            <div style="font-size: 0.9rem; color: #666; margin-top: 0.3rem;">Search for users by query term</div>
          </div>
          <div style="padding: 0.8rem; background: #f8f9fa; border-radius: 6px; border-left: 3px solid #0b5ed7;">
            <strong style="color: #0b5ed7;">GET/POST /flag</strong>
            <div style="font-size: 0.9rem; color: #666; margin-top: 0.3rem;">Submit the 3 users' secret_key values to claim the flag</div>
          </div>
        </div>
      </section>
      <footer>© 2025 CTF Banking Summit</footer>
    </main>
  </body>
</html>
"""
    return Response(html, mimetype="text/html")


def extract_session_token() -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token_candidate = auth_header.split(" ", 1)[1].strip()
        if token_candidate:
            return token_candidate

    cookie_token = request.cookies.get(JWT_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    return None


def decode_session_jwt(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        options={"require": ["exp", "iat", "iss", "sub"]},
    )


def wants_html_response() -> bool:
    accept = request.accept_mimetypes
    if not accept:
        return True
    preferred = accept.best_match(
        ["text/html", "application/xhtml+xml", "application/json"],
        default="text/html",
    )
    return preferred in {"text/html", "application/xhtml+xml"}


def make_unauthorized_response(error_code: str, status_code: int = 401) -> Response:
    if request.method == "GET" and wants_html_response():
        return redirect(url_for("authenticate_team"))

    payload = {"error": error_code}
    resp = jsonify(payload)
    resp.status_code = status_code
    return resp


def rate_limit_response(error_code: str, retry_after_seconds: float) -> Response:
    retry_after_seconds = max(0.0, retry_after_seconds)
    retry_after_header = max(0, int(math.ceil(retry_after_seconds)))
    payload = {
        "error": error_code,
        "retry_after": round(retry_after_seconds, 2),
        "limit": RATE_LIMIT_MAX_REQUESTS,
        "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
        "minimum_interval_seconds": RATE_LIMIT_MIN_INTERVAL,
    }
    resp = jsonify(payload)
    resp.status_code = 429
    resp.headers["Retry-After"] = str(retry_after_header)
    return resp


def enforce_rate_limit(team_token: str) -> Optional[Response]:
    now = time.time()
    r = get_redis_client()
    if r is None:
        # Fallback to in-memory
        with RATE_LIMIT_LOCK:
            state = RATE_LIMIT_STATE.get(team_token)
            if not state or now - state.get("window_start", 0) >= RATE_LIMIT_WINDOW_SECONDS:
                state = {
                    "window_start": now,
                    "count": 0,
                    "last_request": None,
                }
                RATE_LIMIT_STATE[team_token] = state

            if state["count"] >= RATE_LIMIT_MAX_REQUESTS:
                reset_at = state["window_start"] + RATE_LIMIT_WINDOW_SECONDS
                retry_after = max(0.0, reset_at - now)
                logger.info(
                    "Rate limit reached for team %s: %s requests/%ss", team_token, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
                )
                return rate_limit_response("too_many_requests", retry_after)

            last_request = state.get("last_request")
            if last_request is not None:
                since_last = now - last_request
                if since_last < RATE_LIMIT_MIN_INTERVAL:
                    retry_after = RATE_LIMIT_MIN_INTERVAL - since_last
                    logger.debug(
                        "Rate limit spacing hit for team %s: last %.2fs ago (min %.2fs)",
                        team_token,
                        since_last,
                        RATE_LIMIT_MIN_INTERVAL,
                    )
                    return rate_limit_response("too_many_requests", retry_after)

            state["count"] += 1
            state["last_request"] = now
            remaining = max(0, RATE_LIMIT_MAX_REQUESTS - state["count"])

        logger.info(
            "RL team=%s count=%d/%d remaining=%d spacing=%.1fs window_started=%d",
            team_token,
            state["count"],
            RATE_LIMIT_MAX_REQUESTS,
            remaining,
            RATE_LIMIT_MIN_INTERVAL,
            int(state["window_start"]),
        )
        return None

    # Redis-backed rate limiting (fixed window + min spacing)
    window_id = int(now // RATE_LIMIT_WINDOW_SECONDS)
    k_count = f"{REDIS_PREFIX}:rl:{team_token}:w:{window_id}"
    k_last = f"{REDIS_PREFIX}:rl:{team_token}:last"

    # Enforce minimum spacing first
    try:
        last_ts_raw = r.get(k_last)
        if last_ts_raw is not None:
            try:
                last_ts = float(last_ts_raw)
            except ValueError:
                last_ts = None
            if last_ts is not None:
                since_last = now - last_ts
                if since_last < RATE_LIMIT_MIN_INTERVAL:
                    retry_after = RATE_LIMIT_MIN_INTERVAL - since_last
                    return rate_limit_response("too_many_requests", retry_after)
    except Exception:
        # If Redis read fails, fall back to allowing spacing and continue
        pass

    # Count within fixed window
    try:
        count = r.incr(k_count)
        if count == 1:
            # Set expiry slightly longer than window to cover clock skew
            r.expire(k_count, int(RATE_LIMIT_WINDOW_SECONDS) + 2)
        if count > RATE_LIMIT_MAX_REQUESTS:
            reset_at = (window_id + 1) * RATE_LIMIT_WINDOW_SECONDS
            retry_after = max(0.0, reset_at - now)
            logger.info(
                "[Redis] Rate limit reached team=%s count=%s/%s", team_token, count, RATE_LIMIT_MAX_REQUESTS
            )
            return rate_limit_response("too_many_requests", retry_after)
        # Update last request timestamp
        try:
            r.set(k_last, str(now), ex=max(int(RATE_LIMIT_WINDOW_SECONDS), int(RATE_LIMIT_MIN_INTERVAL) + 1))
        except Exception:
            pass
    except Exception:
        logger.exception("Redis error during rate limit; allowing request")
        return None

    remaining = max(0, RATE_LIMIT_MAX_REQUESTS - int(count))
    logger.info("RL[redis] team=%s count=%d/%d remaining=%d spacing=%.1fs window=%d",
                team_token, int(count), RATE_LIMIT_MAX_REQUESTS, remaining, RATE_LIMIT_MIN_INTERVAL, window_id)
    return None


@app.get("/users/<int:user_id>")
def get_user(user_id: int):
    """Return a user record by numeric ID."""
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(row_to_dict(row))


@app.get("/search")
def search():
    """Search users by username fragment and return matching records."""
    q = request.args.get("q", "")
    conn = get_db()
    cur = conn.cursor()
    sql = (
        "SELECT id, username, email, phone, address, dob, ssn, "
        "credit_card_number, credit_card_cvv, credit_card_exp, api_token, secret_key "
        f"FROM users WHERE username LIKE '%{q}%';"
    )
    try:
        rows = cur.execute(sql).fetchall()
        data = [row_to_dict(r) for r in rows]
        return jsonify({"q": q, "results": data})
    except Exception:
        app.logger.exception("Search query failed for %r", q)
        return jsonify({"q": q, "error": "query_failed"}), 400
    finally:
        conn.close()


# @app.get("/export")
def export_csv():
    """Return search results in CSV format."""
    q = request.args.get("q", "")
    conn = get_db()
    cur = conn.cursor()
    sql = (
        "SELECT id, username, email, phone, address, dob, ssn, "
        "credit_card_number, credit_card_cvv, credit_card_exp, api_token, secret_key "
        f"FROM users WHERE username LIKE '%{q}%';"
    )
    try:
        rows = cur.execute(sql).fetchall()
        # Minimal CSV without quoting to keep it simple for CTF
        headers = [
            "id","username","email","phone","address","dob","ssn",
            "credit_card_number","credit_card_cvv","credit_card_exp","api_token","secret_key"
        ]
        lines = [",".join(headers)]
        for r in rows:
            vals = [str(r[h]) if r[h] is not None else "" for h in headers]
            lines.append(",".join(v.replace("\n"," ").replace(",",";") for v in vals))
        body = "\n".join(lines) + "\n"
        return Response(body, mimetype="text/csv")
    except Exception:
        app.logger.exception("CSV export failed for %r", q)
        return Response("status,error\nmessage,query_failed\n", mimetype="text/csv", status=400)
    finally:
        conn.close()


@app.route("/flag", methods=["GET", "POST"])
def flag_endpoint():
    """Verify three users' secret_key values and return the flag.

    Accepts either JSON (preferred) or form submissions.
    JSON formats accepted:
      - {"keys": ["...","...","..."]}
      - {"k1": "...", "k2": "...", "k3": "..."}
      - {"s1": "...", "s2": "...", "s3": "..."}
      - {"alice": "...", "bob": "...", "charlie": "..."}
    Form fields accepted: k1, k2, k3 (or s1/s2/s3, alice/bob/charlie)
    """
    if request.method == "GET":
        return render_flag_page()

    submitted: list = []

    if request.is_json:
        body = request.get_json(silent=True) or {}
        if isinstance(body.get("keys"), list):
            submitted = [str(x).strip() for x in body.get("keys", []) if isinstance(x, (str, int))]
        else:
            for name in ("k1", "k2", "k3", "s1", "s2", "s3", "alice", "bob", "charlie"):
                v = body.get(name)
                if isinstance(v, (str, int)) and str(v).strip():
                    submitted.append(str(v).strip())

    if not submitted:
        # Accept typical form fields and repeated keys
        for name in ("k1", "k2", "k3", "s1", "s2", "s3", "alice", "bob", "charlie"):
            v = request.form.get(name)
            if v:
                submitted.append(v.strip())
        for v in request.values.getlist("keys"):
            if v:
                submitted.append(v.strip())

    # Fetch the 3 secret keys from DB (seeded users)
    conn = get_db()
    try:
        rows = conn.execute("SELECT secret_key FROM users ORDER BY id ASC").fetchall()
    finally:
        conn.close()
    db_keys = [r["secret_key"] for r in rows]

    if len(db_keys) != 3:
        # Challenge expects exactly 3 users
        if wants_html_response():
            return render_flag_page("Máy chủ chưa được khởi tạo đúng (users != 3)."), 500
        return jsonify({"error": "server_misconfigured"}), 500

    if len(submitted) != 3:
        if wants_html_response():
            return render_flag_page("Cần nhập đủ 3 secret_key."), 400
        return jsonify({"error": "need_three_keys"}), 400

    # Validate (order-insensitive, exact match)
    if set(submitted) == set(db_keys):
        if wants_html_response():
            return render_flag_success_page(FLAG_VALUE)
        return jsonify({"flag": FLAG_VALUE})

    if wants_html_response():
        return render_flag_page("Sai secret_key. Thử lại nhé."), 400
    return jsonify({"error": "mismatch"}), 400


def render_flag_page(message: Optional[str] = None) -> Response:
    stylesheet = url_for("static", filename="css/style.css")
    msg = message or ""
    html = f"""
<!doctype html>
<html lang=\"vi\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Nộp 3 Secret Keys</title>
    <link rel=\"stylesheet\" href=\"{stylesheet}\" />
  </head>
  <body>
    <main>
      <header>
        <div class=\"branding\">
          <h1>AI Fraud Challenge</h1>
          <span class=\"tagline\">Trong DB có tổng cộng 3 users. Player cần phải trích xuất đủ cột secret_key của 3 users để chứng minh bạn đã bypass hoàn toàn hệ thống AI filtering.</span>
        </div>
      </header>
      <section class=\"card\">
        <form method=\"post\" autocomplete=\"off\">
          <label for=\"k1\">Secret Key #1</label>
          <input id=\"k1\" name=\"k1\" type=\"text\" required>
          <label for=\"k2\">Secret Key #2</label>
          <input id=\"k2\" name=\"k2\" type=\"text\" required>
          <label for=\"k3\">Secret Key #3</label>
          <input id=\"k3\" name=\"k3\" type=\"text\" required>
          <p class=\"message\">{msg}</p>
          <button type=\"submit\">Nộp</button>
        </form>
      </section>
      <footer>© 2025 CTF Banking Summit</footer>
    </main>
  </body>
</html>
"""
    return Response(html, mimetype="text/html")


def render_flag_success_page(flag_value: str) -> Response:
    stylesheet = url_for("static", filename="css/style.css")
    html = f"""
<!doctype html>
<html lang=\"vi\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Flag</title>
    <link rel=\"stylesheet\" href=\"{stylesheet}\" />
  </head>
  <body>
    <main>
      <header>
        <div class=\"branding\">
          <h1>Chúc mừng!</h1>
          <span class=\"tagline\">Bạn đã nhập đúng 3 secret_key</span>
        </div>
      </header>
      <section class=\"card\">
        <div style=\"font-size: 1.1rem; color: #333;\"><strong>Flag:</strong> <code>{flag_value}</code></div>
      </section>
      <footer>© 2025 CTF Banking Summit</footer>
    </main>
  </body>
</html>
"""
    return Response(html, mimetype="text/html")

def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
