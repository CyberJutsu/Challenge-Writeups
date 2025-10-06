#!/usr/bin/env bash

# Enhanced DFIR CTF traffic generator with random IP simulation
DURATION=${DURATION:-0}
WORKERS=${WORKERS:-1}
BASE_DELAY=${BASE_DELAY:-2}
JITTER=${JITTER:-3}
ATTACK_MODE=${ATTACK_MODE:-false}
IP_ROTATION=${IP_ROTATION:-true}

APIM_URL=${APIM_URL:-}
CONTAINER_APP_URL=${CONTAINER_APP_URL:-}

# Auto-detect from terraform state
if [[ -z "$APIM_URL" && -f "terraform/terraform.tfstate" ]]; then
  APIM_URL=$(jq -r '.outputs.apim_gateway_url.value // empty' terraform/terraform.tfstate 2>/dev/null || echo "")
  [[ -n "$APIM_URL" ]] && echo "[INFO] Auto-detected APIM_URL=$APIM_URL"
fi

if [[ -z "$CONTAINER_APP_URL" && -f "terraform/terraform.tfstate" ]]; then
  CONTAINER_APP_URL=$(jq -r '.outputs.backend_api_url.value // empty' terraform/terraform.tfstate 2>/dev/null || echo "")
  [[ -n "$CONTAINER_APP_URL" ]] && echo "[INFO] Auto-detected CONTAINER_APP_URL=$CONTAINER_APP_URL"
fi

if [[ -z "$APIM_URL" && -z "$CONTAINER_APP_URL" ]]; then
  echo "[ERROR] No URLs configured"
  exit 1
fi

# Enhanced user agents for realistic simulation
UA_LIST=(
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1"
  "Mozilla/5.0 (Windows NT 10.0; rv:123.0) Gecko/20100101 Firefox/123.0"
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
  "curl/8.4.0"
  "PostmanRuntime/7.39.0"
  "python-requests/2.31.0"
)

# IP ranges for rotation (common VPN/proxy endpoints)
IP_POOLS=(
  "172.202.27.178"
  "20.165.152.4"
  "52.225.85.81"
  "172.172.26.176"
  "172.176.206.187"
  "51.57.74.34"
  "20.171.98.148"
  "172.200.31.247"
  "14.169.74.123"
  "203.144.95.67"
  "1.55.242.89"
  "118.70.186.45"
)

get_ua() {
  echo "${UA_LIST[$((RANDOM % ${#UA_LIST[@]}))]}"
}

get_random_ip() {
  if [[ "$IP_ROTATION" == "true" ]]; then
    echo "${IP_POOLS[$((RANDOM % ${#IP_POOLS[@]}))]}"
  else
    echo ""
  fi
}

do_get() {
  local url="$1"
  local random_ip=$(get_random_ip)
  local curl_opts=(
    -sS -o /dev/null -w '%{http_code}'
    --connect-timeout 10 --max-time 30
    -H "User-Agent: $(get_ua)"
  )

  # Add IP spoofing header for simulation (won't actually change source IP but adds to logs)
  if [[ -n "$random_ip" ]]; then
    curl_opts+=(-H "X-Forwarded-For: $random_ip" -H "X-Real-IP: $random_ip")
  fi

  curl "${curl_opts[@]}" "$url" 2>/dev/null || echo "000"
}

post_json() {
  local url="$1" json="$2"
  local random_ip=$(get_random_ip)
  local curl_opts=(
    -sS -o /dev/null -w '%{http_code}'
    --connect-timeout 10 --max-time 30
    -H "User-Agent: $(get_ua)"
    -H 'Content-Type: application/json'
    -d "$json" -X POST
  )

  # Add IP spoofing headers
  if [[ -n "$random_ip" ]]; then
    curl_opts+=(-H "X-Forwarded-For: $random_ip" -H "X-Real-IP: $random_ip")
  fi

  curl "${curl_opts[@]}" "$url" 2>/dev/null || echo "000"
}

post_form() {
  local url="$1" field="$2" value="$3"
  local random_ip=$(get_random_ip)
  local curl_opts=(
    -sS -o /dev/null -w '%{http_code}'
    --connect-timeout 10 --max-time 30
    -H "User-Agent: $(get_ua)"
    -F "${field}=${value}"
  )

  # Add IP spoofing headers
  if [[ -n "$random_ip" ]]; then
    curl_opts+=(-H "X-Forwarded-For: $random_ip" -H "X-Real-IP: $random_ip")
  fi

  curl "${curl_opts[@]}" "$url" 2>/dev/null || echo "000"
}

# Enhanced payload generation for DFIR scenarios
rand_amount() {
  local mode=$((RANDOM % 100))
  if [[ "$ATTACK_MODE" == "true" && $mode -lt 20 ]]; then
    # 20% suspicious amounts in attack mode
    local suspicious=("555512" "999999" "1000000" "123456789" "0.01" "9999999.99")
    echo "${suspicious[$((RANDOM % ${#suspicious[@]}))]}"
  elif [[ $mode -lt 80 ]]; then
    # 80% normal amounts
    printf "%.2f" $(echo "scale=2; ($RANDOM % 10000 + 100) / 100" | bc 2>/dev/null || echo "25.00")
  else
    # 20% slightly unusual but not suspicious
    printf "%.2f" $(echo "scale=2; ($RANDOM % 50000 + 10000) / 100" | bc 2>/dev/null || echo "150.00")
  fi
}

rand_user() {
  local mode=$((RANDOM % 100))
  if [[ "$ATTACK_MODE" == "true" && $mode -lt 15 ]]; then
    # Suspicious usernames in attack mode
    local suspicious=("admin" "root" "test" "dontexist" "system" "service" "backdoor")
    echo "${suspicious[$((RANDOM % ${#suspicious[@]}))]}"
  else
    # Normal usernames
    local normal=("alice" "bob" "charlie" "diana" "emma" "frank" "grace" "henry")
    echo "${normal[$((RANDOM % ${#normal[@]}))]}"
  fi
}

rand_message() {
  local mode=$((RANDOM % 100))
  if [[ "$ATTACK_MODE" == "true" && $mode -lt 10 ]]; then
    # SSTI payloads (10% in attack mode)
    local payloads=(
      "<%= 7*7 %>"
      "<%= global.process.version %>"
      "test123123"
      "<%= require('fs').readFileSync('/etc/passwd') %>"
      "normal payment message"
    )
    echo "${payloads[$((RANDOM % ${#payloads[@]}))]}"
  else
    # Normal messages
    local messages=("Payment for services" "Thanks!" "Monthly subscription" "Gift payment" "Invoice #$((RANDOM % 9999))" "")
    echo "${messages[$((RANDOM % ${#messages[@]}))]}"
  fi
}

hit_endpoints() {
  local worker_id="$1"
  local current_ip=$(get_random_ip)

  echo "[$(date '+%H:%M:%S')] Worker#$worker_id using IP: ${current_ip:-'default'}"

  # APIM endpoints (focus on payment API as requested)
  if [[ -n "$APIM_URL" ]]; then
    # Main page
    local code=$(do_get "$APIM_URL/")
    echo "[$(date '+%H:%M:%S')] Worker#$worker_id apim GET / -> $code"

    # Payment API with enhanced payload variation
    local amount=$(rand_amount)
    local recipient=$(rand_user)
    local message=$(rand_message)
    local payload='{"amount":"'"$amount"'","recipient":"'"$recipient"'","message":"'"$message"'"}'

    code=$(post_json "$APIM_URL/api/payment" "$payload")
    echo "[$(date '+%H:%M:%S')] Worker#$worker_id apim POST /api/payment [$amount->$recipient] -> $code"

    # In attack mode, occasionally follow up with scan attempts
    if [[ "$ATTACK_MODE" == "true" && $((RANDOM % 100)) -lt 30 ]]; then
      # Try to scan the generated QR (simulating exploitation attempt)
      sleep 1
      local blob_url="https://qrwebsax3zov6py.blob.core.windows.net/qrcodes/qr_1757355362755_108.png"
      code=$(post_form "$APIM_URL/api/scan" "imageUrl" "$blob_url")
      echo "[$(date '+%H:%M:%S')] Worker#$worker_id apim POST /api/scan (exploit attempt) -> $code"
    fi

    # Random static resource requests (realistic browsing)
    if [[ $((RANDOM % 100)) -lt 40 ]]; then
      local resources=("js/main.js" "js/qr-generator.js" "js/ui-tabs.js" "css/main.css")
      local resource="${resources[$((RANDOM % ${#resources[@]}))]}"
      code=$(do_get "$APIM_URL/$resource")
      echo "[$(date '+%H:%M:%S')] Worker#$worker_id apim GET /$resource -> $code"
    fi
  fi

  # Container App direct access (less frequent)
  if [[ -n "$CONTAINER_APP_URL" && $((RANDOM % 100)) -lt 20 ]]; then
    local code=$(do_get "$CONTAINER_APP_URL/")
    echo "[$(date '+%H:%M:%S')] Worker#$worker_id containerapp GET / -> $code"

    local payload='{"amount":"'$(rand_amount)'","recipient":"'$(rand_user)'","message":"'$(rand_message)'"}'
    code=$(post_json "$CONTAINER_APP_URL/api/payment" "$payload")
    echo "[$(date '+%H:%M:%S')] Worker#$worker_id containerapp POST /api/payment -> $code"
  fi
}

worker() {
  local id="$1"
  local start_time=$(date +%s)
  
  echo "[$(date '+%H:%M:%S')] Worker #$id started"
  
  while true; do
    hit_endpoints "$id"
    
    # Check duration
    if [[ $DURATION -gt 0 ]]; then
      local now=$(date +%s)
      if [[ $((now - start_time)) -ge $DURATION ]]; then
        echo "[$(date '+%H:%M:%S')] Worker #$id finished"
        break
      fi
    fi
    
    # Sleep with jitter
    local sleep_time=$((BASE_DELAY + (JITTER > 0 ? RANDOM % (JITTER + 1) : 0)))
    sleep "$sleep_time"
  done
}

# Main
echo "=== Enhanced DFIR CTF Traffic Generator ==="
echo "Workers: $WORKERS, Duration: ${DURATION}s (0=infinite)"
echo "Attack Mode: $ATTACK_MODE, IP Rotation: $IP_ROTATION"
echo "Base Delay: ${BASE_DELAY}s, Jitter: ${JITTER}s"
echo "Targets:"
[[ -n "$CONTAINER_APP_URL" ]] && echo "  Container App: $CONTAINER_APP_URL"
[[ -n "$APIM_URL" ]] && echo "  APIM: $APIM_URL"
echo ""

# Show sample payloads in attack mode
if [[ "$ATTACK_MODE" == "true" ]]; then
  echo "=== Attack Mode Enabled ==="
  echo "Sample suspicious payloads will be included:"
  echo "  - SSTI injection attempts"
  echo "  - Suspicious amounts (555512, 999999, etc.)"
  echo "  - Suspicious usernames (admin, root, dontexist)"
  echo "  - Exploitation scanning attempts"
  echo ""
fi

# Start workers
pids=()
for ((i=1; i<=WORKERS; i++)); do
  worker "$i" &
  pids+=("$!")
done

# Signal handler
cleanup() {
  echo ""
  echo "Stopping workers..."
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  echo "Done."
  exit 0
}

trap cleanup INT TERM

# Wait for workers
if [[ $DURATION -gt 0 ]]; then
  for pid in "${pids[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
  echo "All workers completed."
else
  wait "${pids[0]}" 2>/dev/null || true
fi