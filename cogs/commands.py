import discord
from discord.ext import commands
import aiosqlite

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Use app_commands instead of commands.slash_command
    @discord.app_commands.command(name="checkalts", description="Check known alts for a SteamID")
    async def check_alts(self, interaction: discord.Interaction, steamid: str):
        async with aiosqlite.connect("alts.db") as db:
            cursor = await db.execute("SELECT ip FROM players WHERE steamid=?", (steamid,))
            ips = await cursor.fetchall()

            alts = []
            for ip in ips:
                cur2 = await db.execute(
                    "SELECT steamid FROM players WHERE ip=? AND steamid!=?",
                    (ip[0], steamid)
                )
                alts.extend(await cur2.fetchall())

        if not alts:
            await interaction.response.send_message(f"No alts found for `{steamid}`.")
            return

        embed = discord.Embed(
            title=f"Alt Accounts for {steamid}",
            description="Click a button below to view details",
            color=discord.Color.blue()
        )
        view = discord.ui.View()

        for alt in alts:
            button = discord.ui.Button(label=alt[0], style=discord.ButtonStyle.secondary)

            async def button_callback(interaction: discord.Interaction, alt=alt[0]):
                await interaction.response.send_message(
                    f"🔎 Alt account detected: **{alt}**",
                    ephemeral=True
                )

            button.callback = button_callback
            view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))