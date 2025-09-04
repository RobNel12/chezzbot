from discord.ext import commands, tasks
from mcrcon import MCRcon
import aiosqlite
import re
import os

CREATE_PLAYERS = """
CREATE TABLE IF NOT EXISTS players (
  playfab_id TEXT,
  ip TEXT,
  last_seen INTEGER,
  PRIMARY KEY (playfab_id, ip)
);
"""

# Cache table for optional PlayFab enrichment
CREATE_PROFILES = """
CREATE TABLE IF NOT EXISTS profiles (
  playfab_id TEXT PRIMARY KEY,
  display_name TEXT,
  avatar_url TEXT,
  steam_id TEXT,
  epic_id TEXT,
  last_updated INTEGER
);
"""

class RconCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rcon_task.start()

    def cog_unload(self):
        self.rcon_task.cancel()

    @tasks.loop(seconds=30)
    async def rcon_task(self):
        host = os.getenv("RCON_HOST", "127.0.0.1")
        port = int(os.getenv("RCON_PORT", "27015"))
        password = os.getenv("RCON_PASSWORD", "")

        try:
            with MCRcon(host, password, port=port) as mcr:
                resp = mcr.command("Players")
                lines = [ln.strip() for ln in resp.splitlines() if ln.strip()]

            async with aiosqlite.connect("alts.db") as db:
                await db.execute(CREATE_PLAYERS)
                await db.execute(CREATE_PROFILES)
                await db.commit()

                # EXAMPLE expected fragments in lines:
                # "Name: Foo | PlayFabID: 123ABC456DEF789 | IP: 10.0.0.5"
                # Adjust these regexes to match your server's output
                for line in lines:
                    m = re.search(r"PlayFab(?:ID)?\s*:\s*([A-Za-z0-9]+)", line)
                    ipm = re.search(r"\bIP\s*:\s*([\d\.]+)", line)
                    if not m or not ipm:
                        continue
                    playfab_id = m.group(1)
                    ip = ipm.group(1)

                    await db.execute(
                        "INSERT OR REPLACE INTO players (playfab_id, ip, last_seen) VALUES (?, ?, strftime('%s','now'))",
                        (playfab_id, ip)
                    )
                    await db.commit()

                    # Fire custom event for detection flow
                    self.bot.dispatch("player_detected", playfab_id, ip)

        except Exception as e:
            print("RCON error:", e)

async def setup(bot):
    await bot.add_cog(RconCog(bot))