#!/usr/bin/env bash
# Shiri-Presentation-BOT — serwerde 1 kommanda bilen gurnamak (Ubuntu / Debian).
# Gaýtadan işletseňiz: kody täzeläp, boty täzeden başladýar (.env saklanýar).
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/k9032431-cmd/Presentation-bot.git}"
BRANCH="${BRANCH:-claude/amazing-dirac-9qiwys}"
APP_DIR="${APP_DIR:-/opt/shiri-presentation-bot}"
SERVICE="shiri-presentation-bot"

say() { echo -e "\n\033[1;36m==> $*\033[0m"; }
ask() { # ask VAR "Sorag" [optional]
  local __v=""
  while :; do
    read -r -p "$2: " __v </dev/tty || true
    [[ -n "$__v" || "${3:-}" == "optional" ]] && break
    echo "  Bu meýdan hökmany."
  done
  printf -v "$1" '%s' "$__v"
}

if [[ $EUID -ne 0 ]]; then
  echo "Root hökmünde işlediň:  sudo bash install.sh"; exit 1
fi

say "Gerekli paketler gurnalýar..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git python3 python3-venv python3-pip fonts-dejavu-core >/dev/null

PYV=$(python3 -c 'import sys; print(sys.version_info >= (3, 10))')
if [[ "$PYV" != "True" ]]; then
  echo "Python 3.10+ gerek (Ubuntu 22.04 ýa-da täzesi). Häzirki: $(python3 --version)"; exit 1
fi

say "Kod göçürilýär: $APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" fetch -q origin "$BRANCH"
  git -C "$APP_DIR" checkout -q -B "$BRANCH" FETCH_HEAD
else
  git clone -q --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

say "Python gurşawy taýýarlanýar..."
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

if [[ ! -f "$APP_DIR/.env" ]]; then
  say "Bot sazlamalary (diňe ilkinji gezek soralýar)"
  ask BOT_TOKEN "Telegram BOT_TOKEN (@BotFather)"
  ask ADMIN_IDS "Admin Telegram ID (@userinfobot; birnäçe bolsa: 111,222)"
  ask ANTHROPIC_API_KEY "Claude API açary (console.anthropic.com)"
  ask PEXELS_API_KEY "Pexels API açary (islege görä, boş goýup bilersiňiz)" optional
  umask 077
  cat > "$APP_DIR/.env" <<EOF
BOT_TOKEN=$BOT_TOKEN
ADMIN_IDS=$ADMIN_IDS
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
CLAUDE_MODEL=claude-opus-5-5
PEXELS_API_KEY=$PEXELS_API_KEY
EOF
fi

say "systemd hyzmaty döredilýär..."
cat > "/etc/systemd/system/$SERVICE.service" <<EOF
[Unit]
Description=Shiri-Presentation-BOT (Telegram)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python -m bot.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable -q "$SERVICE"
systemctl restart "$SERVICE"
sleep 3

if systemctl is-active -q "$SERVICE"; then
  say "✅ Shiri-Presentation-BOT işledi!"
else
  say "⚠️ Bot başlamady. Loglary görüň:"
  journalctl -u "$SERVICE" -n 30 --no-pager
fi

cat <<EOF

Peýdaly kommandalar:
  Ýagdaýy:        systemctl status $SERVICE
  Loglar:         journalctl -u $SERVICE -f
  Täzeden başlat: systemctl restart $SERVICE
  Togtat:         systemctl stop $SERVICE
  Sazlamalar:     nano $APP_DIR/.env   (soň: systemctl restart $SERVICE)
  Täzelemek:      sudo bash $APP_DIR/install.sh
EOF
