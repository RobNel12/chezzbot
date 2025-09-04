import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

INITIAL_COGS = ["cogs.rcon", "cogs.detection", "cogs.commands"]

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Slash command sync failed: {e}")

async def main():
    for ext in INITIAL_COGS:
        await bot.load_extension(ext)
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())