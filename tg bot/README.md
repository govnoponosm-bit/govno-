# Telegram-бот: поиск фильмов по коду

## Возможности

- Поиск фильма по коду
- Обязательные подписки (бессрочные и на срок)
- Админ-панель: фильмы, подписки, рассылка постов

## Установка

```powershell
cd "путь\к\tg bot"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

В `.env`:

```env
BOT_TOKEN=токен_от_BotFather
ADMIN_IDS=123456789
```

`ADMIN_IDS` — только цифры ([@userinfobot](https://t.me/userinfobot)).

## Запуск

```powershell
.\.venv\Scripts\python.exe bot.py
```

Остановка: `Ctrl+C`

## Структура

```
bot.py
config.py
database.py
keyboards.py
middlewares.py
states.py
handlers/
services/
requirements.txt
.env.example
```

База данных: `bot.db` (создаётся автоматически).
