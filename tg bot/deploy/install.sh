#!/bin/bash
set -e
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Сначала создайте файл .env с BOT_TOKEN и ADMIN_IDS"
  exit 1
fi

apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp deploy/tgbot.service /etc/systemd/system/tgbot.service
sed -i "s|/opt/tg-bot|$(pwd)|g" /etc/systemd/system/tgbot.service

systemctl daemon-reload
systemctl enable tgbot
systemctl start tgbot
echo "Бот запущен! Проверка: systemctl status tgbot"
