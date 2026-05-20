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
REMOTE_CMD="git -C $REMOTE_DIR pull origin master && echo 'TuRasero.com' | sudo -S systemctl restart $SERVICE && echo 'Servicio reiniciado OK'"

# Intentar con sshpass (WSL/Linux) o plink (Windows)
if command -v sshpass &>/dev/null; then
  sshpass -p 'TuRasero.com' ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$REMOTE_CMD"
elif [ -f "/mnt/c/Program Files/PuTTY/plink.exe" ]; then
  echo yes | "/mnt/c/Program Files/PuTTY/plink.exe" -pw 'TuRasero.com' "$REMOTE_USER@$REMOTE_HOST" "$REMOTE_CMD"
else
  echo "ERROR: Instala sshpass (sudo apt install sshpass) o PuTTY"
  exit 1
fi

echo ""
echo "Despliegue completado."
