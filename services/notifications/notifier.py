import os
import asyncio
from telegram import Bot
from telegram.error import TelegramError

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

class Notifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.bot = None
        if self.token:
            self.bot = Bot(token=self.token)

    async def send_alert(self, message: str):
        if not self.bot or not self.chat_id:
            print(f"Alert (Not Configured): {message}")
            return

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=f"🚨 Skynet Alert:\n{message}")
        except TelegramError as e:
            print(f"Failed to send Telegram alert: {e}")
        except Exception as e:
            print(f"Unexpected error in notifier: {e}")

notifier = Notifier()
