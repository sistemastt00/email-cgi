#!/bin/bash
SRC="/mnt/c/Users/Sistemas/Documents/FastAPI/FastAPI - Email CGI"
DST="/home/sistemas/email-cgi"
rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' --exclude='start.bat' "$SRC/" "$DST/"
echo Tutrastero00 | sudo -S systemctl restart email-cgi
echo "Deploy completado"
sudo systemctl status email-cgi --no-pager | tail -3
