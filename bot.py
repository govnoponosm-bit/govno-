import os
import logging
from telegram import Update, WebhookInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://example.com")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Я бот. 👋")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Доступные команды:\n/start - начать\n/help - помощь")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Ты написал: {update.message.text}")

async def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    await application.initialize()
    await application.start()
    
    # Set webhook
    try:
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")
    except TelegramError as e:
        logger.error(f"Failed to set webhook: {e}")
    
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path="/webhook",
        webhook_url=f"{WEBHOOK_URL}/webhook"
    )
    
    await application.idle()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
