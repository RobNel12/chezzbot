from discord.ext import commands
import discord
import aiosqlite
import os
import time

ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID", "0"))

# Optional: PlayFab enrichment (grabs display name, avatar, linked accounts)
USE_PLAYFAB = bool(os.getenv("PLAYFAB_SECRET_KEY"))
if USE_PLAYFAB:
    from PlayFab import PlayFabSettings
    from PlayFab.PlayFabServerAPI import GetPlayerProfile, GetUserAccountInfo
    PlayFabSettings.TitleId = os.getenv("PLAYFAB_TITLE_ID", "")
    PlayFabSettings.DeveloperSecretKey = os.getenv("PLAYFAB_SECRET_KEY", "")

async def get_playfab_profile(db, playfab_id: str):
    """Returns (display_name, avatar_url, steam_id, epic_id) or cached values, stores cache."""
    # Serve cached within 6 hours
    cur = await db.execute("SELECT display_name, avatar_url, steam_id, epic_id, last_updated FROM profiles WHERE playfab_id=?", (playfab_id,))
    row = await cur.fetchone()
    now = int(time.time())
    if row and now - (row[4] or 0) < 6 * 3600:
        return row[0], row[1], row[2], row[3]

    if not USE_PLAYFAB:
        return None, None, None, None

    try:
        prof = GetPlayerProfile({"PlayFabId": playfab_id, "ProfileConstraints": {"ShowDisplayName": True, "ShowLinkedAccounts": True}})
        display = None
        avatar = None
        steam_id = None
        epic_id = None

        if prof and prof.get("code") == 200:
            pdata = prof["data"].get("PlayerProfile", {})
            display = pdata.get("DisplayName")
            # try player avatar URL if present in profile
            avatar = pdata.get("AvatarUrl")

        # Linked accounts via account info
        acc = GetUserAccountInfo({"PlayFabId": playfab_id})
        if acc and acc.get("code") == 200:
            info = acc["data"].get("UserInfo", {})
            links = info.get("TitleInfo", {}).get("TitlePlayerAccounts", []) or []
            # Some titles expose linked ids differently; also check UserAccountInfo keys
            # Steam/Epic can also appear in UserAccountInfo["SteamInfo"] / ["CustomIdInfo"] / etc.
            steam_info = info.get("SteamInfo")
            if steam_info and steam_info.get("SteamId"):
                steam_id = str(steam_info["SteamId"])

            # Epic can be attached as "CustomIdInfo" or via LinkedAccounts depending on your title setup.
            # We’ll scan TitlePlayerAccounts as a fallback for an "epic" tag in Username or Platform
            for l in links:
                plat = (l.get("Platform") or "").lower()
                if "epic" in plat:
                    epic_id = l.get("Username") or l.get("PlatformUserId") or epic_id

        await db.execute(
            "INSERT OR REPLACE INTO profiles (playfab_id, display_name, avatar_url, steam_id, epic_id, last_updated) VALUES (?, ?, ?, ?, ?, ?)",
            (playfab_id, display, avatar, steam_id, epic_id, now)
        )
        await db.commit()
        return display, avatar, steam_id, epic_id

    except Exception:
        return None, None, None, None

class DetectionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_player_detected(self, playfab_id, ip):
        async with aiosqlite.connect("alts.db") as db:
            cur = await db.execute(
                "SELECT playfab_id FROM players WHERE ip=? AND playfab_id!=?",
                (ip, playfab_id)
            )
            alts = [row[0] for row in await cur.fetchall()]

            display, avatar, steam_id, epic_id = await get_playfab_profile(db, playfab_id)

        if not alts or not ALERT_CHANNEL_ID:
            return

        channel = self.bot.get_channel(ALERT_CHANNEL_ID)

        title = "⚠️ Possible Alt Detected"
        desc_lines = [
            f"**PlayFabID:** `{playfab_id}`",
            f"**IP:** `{ip}`"
        ]
        if display:
            desc_lines.insert(0, f"**Player:** {display}")
        if steam_id or epic_id:
            id_bits = []
            if steam_id: id_bits.append(f"Steam: `{steam_id}`")
            if epic_id: id_bits.append(f"Epic: `{epic_id}`")
            desc_lines.append("**Linked Accounts:** " + " | ".join(id_bits))

        embed = discord.Embed(
            title=title,
            description="\n".join(desc_lines),
            color=discord.Color.red()
        )
        embed.add_field(
            name="Other PlayFabIDs on Same IP",
            value="\n".join(f"`{a}`" for a in alts),
            inline=False
        )
        embed.set_footer(text="Mordhau Alt Detection (PlayFab)")

        if avatar:
            embed.set_thumbnail(url=avatar)

        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DetectionCog(bot))