from discord.ext import commands
import discord
import aiosqlite
import os

ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID", 0))

class DetectionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_player_detected(self, steamid, ip):
        async with aiosqlite.connect("alts.db") as db:
            cursor = await db.execute(
                "SELECT steamid FROM players WHERE ip=? AND steamid!=?",
                (ip, steamid)
            )
            alts = await cursor.fetchall()

        if alts and ALERT_CHANNEL_ID:
            channel = self.bot.get_channel(ALERT_CHANNEL_ID)

            embed = discord.Embed(
                title="⚠️ Possible Alt Detected",
                description=f"**SteamID:** `{steamid}`\n**IP:** `{ip}`",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Other Accounts on Same IP",
                value="\n".join([a[0] for a in alts]),
                inline=False
            )
            embed.set_footer(text="Mordhau Alt Detection Bot")

            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DetectionCog(bot))
