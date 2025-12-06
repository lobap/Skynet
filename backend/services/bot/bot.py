import asyncio
import json
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from ..agent import orchestrator
from ..database import database
from sqlalchemy.orm import Session

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../backend/.env'))

TOKEN = os.getenv('TELEGRAM_TOKEN')

class DummyWS:
    def __init__(self):
        self.messages = []

    async def send_text(self, text):
        data = json.loads(text)
        self.messages.append(data)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    db = database.SessionLocal()
    ws = DummyWS()
    await orchestrator.run_agent_loop(user_message, ws, db)
    response = "\n".join([f"{m['role'].replace('agent-', '')}: {m['content']}" for m in ws.messages[-5:]])
    await update.message.reply_text(response)
    db.close()

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()