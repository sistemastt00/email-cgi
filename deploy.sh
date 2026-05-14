#!/bin/bash
set -e

PROJECT_LOCAL="/mnt/c/Users/Sistemas/Documents/FastAPI/FastAPI - Email CGI"
REMOTE_USER="paucosta"
REMOTE_HOST="192.168.2.197"
REMOTE_DIR="/opt/fastapi-email-cgi"
SERVICE="fastapi-email-cgi"

MSG=${1:-"Actualización"}

echo "==> Push a GitHub..."
cd "$PROJECT_LOCAL"
git add -A
git commit -m "$MSG" 2>/dev/null || echo "    (sin cambios nuevos que commitear)"
git push

echo "==> git pull en el servidor..."
sshpass -p 'TuRasero.com' ssh -o StrictHostKeyChecking=no \
  "$REMOTE_USER@$REMOTE_HOST" \
  "git -C $REMOTE_DIR pull origin master && sudo systemctl restart $SERVICE && echo 'Servicio reiniciado OK'"

echo ""
echo "Despliegue completado."
