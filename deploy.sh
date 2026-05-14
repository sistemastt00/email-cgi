#!/bin/bash
set -e
MSG="${1:-update}"
SERVER="paucosta@192.168.2.197"
PASS="TuRasero.com"
REMOTE_DIR="/opt/fastapi-email-cgi"
SERVICE="fastapi-email-cgi"
git add -A
git commit -m "$MSG" || echo "Nada nuevo que commitear"
git push
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no "$SERVER" "git -C $REMOTE_DIR pull && sudo systemctl restart $SERVICE && sudo systemctl status $SERVICE --no-pager | tail -5"
echo "Deploy completado -> https://email-cgi.ngrok.dev"