"""
Get Chat ID - Envía este comando para obtener tu chat_id.
Luego lo usaremos en el notificador.
"""

import asyncio
import telegram
from telegram import Bot
from app_config import Config


async def main():
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    updates = await bot.get_updates()
    
    print("📱 ÚltimasMessages:")
    for update in updates[-5:]:
        if update.message:
            chat = update.message.chat
            print(f"  Chat ID: {chat.id} | User: {chat.username or chat.first_name}")
    
    print(f"\n✅ Envía /start al bot en Telegram")
    print(f"   Luego vuelve a correr este script")


if __name__ == "__main__":
    asyncio.run(main())