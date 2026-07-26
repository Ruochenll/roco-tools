#!/bin/bash
# roco-tools 部署脚本
# 用法: bash deploy.sh [--restart]
set -e

cd /var/www/roco-tools

echo ">>> git pull..."
git pull

echo ">>> migrate..."
python3.12 manage.py migrate --noinput 2>/dev/null

echo ">>> collectstatic --clear..."
python3.12 manage.py collectstatic --noinput --clear

echo ">>> restart gunicorn..."
pkill -HUP gunicorn 2>/dev/null || pkill gunicorn; sleep 1
gunicorn config.wsgi --bind 127.0.0.1:8000 --workers 2 --daemon

echo ">>> done"
