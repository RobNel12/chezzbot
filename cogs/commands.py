import discord
from discord.ext import commands
import aiosqlite

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="checkalts", description="Check known alts for a PlayFabID")
    async def check_alts(self, interaction: discord.Interaction, playfab_id: str):
        # Acknowledge immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)

        try:
            async with aiosqlite.connect("alts.db") as db:
                cur = await db.execute("SELECT ip FROM players WHERE playfab_id=?", (playfab_id,))
                ips = [row[0] for row in await cur.fetchall()]

                if not ips:
                    await interaction.followup.send(f"No data for `{playfab_id}`.")
                    return

                alts = set()
                for ip in ips:
                    cur2 = await db.execute(
                        "SELECT playfab_id FROM players WHERE ip=? AND playfab_id!=?",
                        (ip, playfab_id)
                    )
                    alts.update([row[0] for row in await cur2.fetchall()])

            if not alts:
                await interaction.followup.send(f"No alts found for `{playfab_id}`.")
                return

            embed = discord.Embed(
                title=f"Alt Accounts for {playfab_id}",
                description="Click a button below to view details",
                color=discord.Color.blurple()
            )

            view = discord.ui.View(timeout=60)
            for alt in list(alts)[:25]:
                btn = discord.ui.Button(label=alt, style=discord.ButtonStyle.secondary)

                async def cb(i: discord.Interaction, alt=alt):
                    if i.user.id != interaction.user.id:
                        await i.response.send_message("This menu isn't for you.", ephemeral=True)
                        return
                    await i.response.send_message(f"🔎 Alt PlayFabID: `{alt}`", ephemeral=True)

                btn.callback = cb
                view.add_item(btn)

            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            # Always reply even on error
            await interaction.followup.send(f"❌ Error while checking alts: `{e}`")
            raise

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))