from discord.ext import commands, tasks
from mcrcon import MCRcon
import asyncio
import re
import aiosqlite
import os

class RconCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rcon_task.start()

    def cog_unload(self):
        self.rcon_task.cancel()

    @tasks.loop(seconds=30)
    async def rcon_task(self):
        host = os.getenv("RCON_HOST")
        port = int(os.getenv("RCON_PORT"))
        password = os.getenv("RCON_PASSWORD")

        try:
            with MCRcon(host, password, port=port) as mcr:
                resp = mcr.command("Players")
                lines = resp.split("\n")

                async with aiosqlite.connect("alts.db") as db:
                    await db.execute("""CREATE TABLE IF NOT EXISTS players (
                        steamid TEXT,
                        ip TEXT,
                        last_seen INTEGER,
                        PRIMARY KEY (steamid, ip)
                    )""")
                    await db.commit()

                    for line in lines:
                        match = re.search(r"SteamID:\s*(\d+).*IP:\s*([\d.]+)", line)
                        if match:
                            steamid, ip = match.groups()
                            await db.execute(
                                "INSERT OR REPLACE INTO players VALUES (?, ?, strftime('%s','now'))",
                                (steamid, ip)
                            )
                            await db.commit()

                            # Fire custom event
                            self.bot.dispatch("player_detected", steamid, ip)

        except Exception as e:
            print("RCON error:", e)

async def setup(bot):
    await bot.add_cog(RconCog(bot))
