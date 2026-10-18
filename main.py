import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from dotenv import load_dotenv

from database.db import init_db
from cogs.setstartrole import setup as setup_startrole
from cogs.excluderoles import setup as setup_excluderoles
from cogs.settings import setup as setup_settings
from cogs.events import setup as setup_events

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")

if not TOKEN:
    print("❌ DISCORD_TOKEN не найден в .env")
    exit(1)

if not CLIENT_ID:
    print("❌ CLIENT_ID не найден в .env")
    exit(1)


intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",  # Не используется, но нужен для Bot
    intents=intents,
    help_command=None,
    activity=discord.Activity(type=discord.ActivityType.watching, name="за ролями | /help"),
    status=discord.Status.online
)


@bot.event
async def on_ready():
    print(f"✅ {bot.user} готов к работе!")
    print(f"📊 Серверов: {len(bot.guilds)}")
    print(f"👥 Пользователей: {len(bot.users)}")

    # Синхронизация слеш-команд
    try:
        print("🔄 Синхронизация команд...")
        synced = await bot.tree.sync()
        print(f"✅ Синхронизировано {len(synced)} команд")
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")


async def load_cogs():
    await setup_startrole(bot)
    await setup_excluderoles(bot)
    await setup_settings(bot)
    await setup_events(bot)


async def main():
    async with bot:
        await init_db()
        await load_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")