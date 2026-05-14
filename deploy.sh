#!/bin/bash
set -e
MSG="${1:-update}"
WEBHOOK="https://email-cgi.ngrok.dev/deploy"
TOKEN="$(grep DEPLOY_TOKEN /opt/fastapi-email-cgi/.env 2>/dev/null | cut -d= -f2)"

# Fallback: leer desde .env local (WSL)
if [ -z "$TOKEN" ]; then
  ENV_LOCAL="/mnt/c/Users/Sistemas/Documents/FastAPI/FastAPI - Email CGI/.env"
  [ -f "$ENV_LOCAL" ] && TOKEN="$(grep DEPLOY_TOKEN "$ENV_LOCAL" | cut -d= -f2)"
fi

git add -A
git commit -m "$MSG" || echo "Nada nuevo que commitear"
git push

echo "Llamando webhook de deploy..."
RESP=$(curl -s -X POST "${WEBHOOK}?token=${TOKEN}" --max-time 15)
echo "Respuesta: $RESP"
echo "Deploy completado -> https://email-cgi.ngrok.dev"
