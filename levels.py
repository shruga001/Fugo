import discord
from discord.ext import commands
from discord import app_commands
import os
from fns import glob_fns
from decor import decorators


class Levels(commands.Cog):
    """
    Cog for levelling system — user progress tracking, rank lists,
    and admin-level management commands.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("Levels cog registered")

    # ──────────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────────

    def _get_user_xp_data(self, user_id: int, guild_id):
        """Return the XP dict for a user in a guild, or None."""
        data = glob_fns().load_json(f"users_data/{user_id}.json")
        if data is None:
            return None
        guild_id = str(guild_id)
        xp_data = data.get("guild_xp", {}).get(guild_id)
        if xp_data is None:
            return None
        return xp_data

    def _get_levels(self):
        """Return the global level thresholds dict."""
        return glob_fns().load_json("guilds_data/guild_levels.json") or {}

    def _get_ranks(self, guild_id):
        """Return rank titles for the given guild (per-guild or global fallback)."""
        guild_id = str(guild_id)
        local = f"guilds_data/{guild_id}/guild_ranks.json"
        if os.path.exists(local):
            return glob_fns().load_json(local) or {}
        return glob_fns().load_json("guilds_data/guild_ranks.json") or {}

    def _xp_for_next_level(self, current_level: int, levels: dict) -> int:
        """Return how much XP is needed to go from current_level to the next level."""
        next_lvl = str(current_level + 1)
        if next_lvl in levels:
            return levels[next_lvl]
        return -1

    def _calculate_progress(self, current_xp: int, current_level: int, levels: dict):
        """
        Return (xp_for_next, xp_for_current, progress_pct) for the progress bar.
        """
        xp_for_current = levels.get(str(current_level), 0)
        xp_for_next = levels.get(str(current_level + 1))
        if xp_for_next is None:
            # Max level reached
            return xp_for_current, xp_for_current, 100.0
        needed = xp_for_next - xp_for_current
        earned = current_xp - xp_for_current
        pct = (earned / needed * 100) if needed > 0 else 0.0
        return xp_for_next, xp_for_current, min(pct, 100.0)

    def _progress_bar(self, pct: float, length: int = 16) -> str:
        """Return a visual progress bar string."""
        filled = round(pct / 100 * length)
        filled = max(0, min(filled, length))
        bar = "█" * filled + "░" * (length - filled)
        return f"{bar} {pct:.1f}%"

    # ──────────────────────────────────────────────
    #  USER-FACING COMMANDS (prefix)
    # ──────────────────────────────────────────────

    @commands.command(name="ranklist", aliases=["ranks", "rank_info"])
    @decorators.is_channel()
    async def ranklist(self, ctx: commands.Context):
        """
        Display every rank title and the level at which it unlocks.
        If no custom ranks are set up for the guild, shows the global defaults.
        """
        ranks = self._get_ranks(ctx.guild.id)
        levels = self._get_levels()

        if not ranks:
            await ctx.send(f"{ctx.author.mention} No ranks have been configured for this server yet.")
            return

        embed = discord.Embed(
            title=f"🏅 {ctx.guild.name} — Rank List",
            description="Ranks and the level they unlock at:",
            color=discord.Color.gold()
        )

        # Build sorted list: rank entries have level as key, rank title as value
        sorted_ranks = sorted(ranks.items(), key=lambda x: int(x[0]))

        # Group into chunks of 10 to avoid field limits
        chunk_size = 10
        for i in range(0, len(sorted_ranks), chunk_size):
            chunk = sorted_ranks[i:i + chunk_size]
            page_num = (i // chunk_size) + 1
            total_pages = (len(sorted_ranks) + chunk_size - 1) // chunk_size
            section_value = ""
            for level_str, rank_title in chunk:
                xp_req = levels.get(level_str, "?")
                section_value += f"**Level {level_str}** — {rank_title} (XP: {xp_req:,})\n"
            embed.add_field(
                name=f"Page {page_num}/{total_pages}",
                value=section_value,
                inline=False
            )

        embed.set_footer(text="Keep chatting to earn XP and level up!")
        await ctx.send(embed=embed)

    @commands.command(name="level", aliases=["myrank", "xp"])
    @decorators.is_channel()
    @decorators.is_user()
    async def my_level(self, ctx: commands.Context):
        """
        Show your current level, XP, and progress toward the next level.
        Also displays your current rank title if one is assigned.
        """
        user_id = ctx.author.id
        guild_id = str(ctx.guild.id)

        # Load user data
        user_data = glob_fns().load_json(f"users_data/{user_id}.json")
        if user_data is None:
            await ctx.send(f"{ctx.author.mention} You are not registered yet! Use `ft!reg` to get started.")
            return

        xp_data = self._get_user_xp_data(user_id, guild_id)
        if xp_data is None:
            await ctx.send(f"{ctx.author.mention} You have no XP data for this guild yet. Start chatting to earn XP!")
            return

        current_level = xp_data["last level"]
        current_xp = xp_data["xp"]
        levels = self._get_levels()
        ranks = self._get_ranks(ctx.guild.id)

        # Current rank title
        user_rank_data = user_data.get("guild_ranks", {}).get(guild_id)
        rank_display = f"**{user_rank_data}**" if user_rank_data else "*No rank assigned yet*"

        # Progress calculation
        xp_for_next, xp_for_current, pct = self._calculate_progress(current_xp, current_level, levels)
        bar = self._progress_bar(pct)

        embed = discord.Embed(
            title=f"📊 {ctx.author.display_name}'s Level Progress",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="Current Level", value=f"**{current_level}**", inline=True)
        embed.add_field(name="Current Rank", value=rank_display, inline=True)
        embed.add_field(name="Total XP", value=f"**{current_xp:,}** XP", inline=True)

        if xp_for_next != -1:
            embed.add_field(
                name=f"Progress to Level {current_level + 1}",
                value=f"`{bar}`\n{current_xp:,} / {xp_for_next:,} XP",
                inline=False
            )
        else:
            embed.add_field(name="Progress", value="🏆 **Max level reached!**", inline=False)

        await ctx.send(embed=embed)

    # ──────────────────────────────────────────────
    #  STAFF / ADMIN COMMANDS (app_commands / slash)
    # ──────────────────────────────────────────────

    @app_commands.command(name="user_level", description="Check the level & XP progress of a specific user")
    @app_commands.describe(member="The member whose level you want to check")
    async def user_level(self, interaction: discord.Interaction, member: discord.Member):
        """
        Staff-only command to view another user's level and XP progress.
        """
        # Permission check: must be staff or co-owner
        guild_data = glob_fns().load_guild(str(interaction.guild.id))
        if guild_data is None:
            await interaction.response.send_message("❌ Guild not set up yet.", ephemeral=True)
            return

        is_allowed = False
        if interaction.user.id in guild_data.get("staff_person", []):
            is_allowed = True
        elif interaction.user.id in guild_data.get("co_owner", []):
            is_allowed = True
        elif interaction.user.id == guild_data.get("owner"):
            is_allowed = True
        elif any(r.id in guild_data.get("staff_roles", []) for r in interaction.user.roles):
            is_allowed = True
        elif any(r.id in guild_data.get("co_owner_roles", []) for r in interaction.user.roles):
            is_allowed = True

        if not is_allowed:
            await interaction.response.send_message(
                "❌ You must be staff or an owner to use this command.", ephemeral=True
            )
            return

        await interaction.response.defer()

        guild_id = str(interaction.guild.id)
        user_data = glob_fns().load_json(f"users_data/{member.id}.json")
        if user_data is None:
            await interaction.followup.send(f"❌ {member.mention} is not registered.")
            return

        xp_data = self._get_user_xp_data(member.id, guild_id)
        if xp_data is None:
            await interaction.followup.send(f"❌ {member.mention} has no XP data for this guild.")
            return

        current_level = xp_data["last level"]
        current_xp = xp_data["xp"]
        levels = self._get_levels()

        xp_for_next, xp_for_current, pct = self._calculate_progress(current_xp, current_level, levels)
        bar = self._progress_bar(pct)

        embed = discord.Embed(
            title=f"📊 {member.display_name}'s Level Progress",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Current Level", value=f"**{current_level}**", inline=True)
        embed.add_field(name="Total XP", value=f"**{current_xp:,}** XP", inline=True)

        if xp_for_next != -1:
            embed.add_field(
                name=f"Progress to Level {current_level + 1}",
                value=f"`{bar}`\n{current_xp:,} / {xp_for_next:,} XP",
                inline=False
            )
        else:
            embed.add_field(name="Progress", value="🏆 **Max level reached!**", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="set_xp", description="Set a user's XP to a specific value (staff/owner only)")
    @app_commands.describe(member="The target member", xp="The new XP value")
    async def set_xp(self, interaction: discord.Interaction, member: discord.Member, xp: int):
        """
        Admin/owner command to directly set a user's XP amount.
        Triggers a level-up check afterward.
        """
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ You must be staff or an owner to use this command.", ephemeral=True)
            return

        if xp < 0:
            await interaction.response.send_message("❌ XP cannot be negative.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        user_path = f"users_data/{member.id}.json"
        user_data = glob_fns().load_json(user_path)

        if user_data is None:
            await interaction.response.send_message(f"❌ {member.mention} is not registered.", ephemeral=True)
            return

        user_data.setdefault("guild_xp", {})
        if guild_id not in user_data["guild_xp"]:
            user_data["guild_xp"][guild_id] = {"last level": 0, "xp": 0}

        user_data["guild_xp"][guild_id]["xp"] = xp
        glob_fns().save_json(user_data, user_path)

        # Recalculate level
        glob_fns().check_level_up(member.id, guild_id)

        await interaction.response.send_message(
            f"✅ Set {member.mention}'s XP to **{xp:,}**. Level has been recalculated.",
            ephemeral=False
        )

    # ──────────────────────────────────────────────
    #  RANK MANAGEMENT COMMANDS (staff / owner)
    # ──────────────────────────────────────────────

    def _get_guild_ranks_path(self, guild_id) -> str:
        """Return the per-guild ranks file path, ensuring it exists."""
        path = f"guilds_data/{guild_id}/guild_ranks.json"
        if not os.path.exists(path):
            # Seed with the global ranks as a starting template
            global_ranks = glob_fns().load_json("guilds_data/guild_ranks.json") or {}
            glob_fns().save_json(global_ranks, path)
        return path

    @app_commands.command(name="add_rank", description="Assign a rank title to a specific level (staff/owner only)")
    @app_commands.describe(level="The level number at which this rank unlocks", rank_name="The name/title for the rank")
    async def add_rank(self, interaction: discord.Interaction, level: int, rank_name: str):
        """
        Add or update a rank title for a given level in this guild.
        Staff/owner only. Writes to the per-guild ranks file.
        """
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ You must be staff or an owner to use this command.", ephemeral=True)
            return

        if level < 0 or level > 99:
            await interaction.response.send_message("❌ Level must be between 0 and 99.", ephemeral=True)
            return

        if len(rank_name.strip()) == 0:
            await interaction.response.send_message("❌ Rank name cannot be empty.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        ranks_path = self._get_guild_ranks_path(guild_id)
        ranks = glob_fns().load_json(ranks_path) or {}

        ranks[str(level)] = rank_name.strip()
        glob_fns().save_json(ranks, ranks_path)

        await interaction.response.send_message(
            f"✅ **Level {level}** is now assigned the rank **\"{rank_name.strip()}\"**.",
            ephemeral=False
        )

    @app_commands.command(name="remove_rank", description="Remove a rank title from a specific level (staff/owner only)")
    @app_commands.describe(level="The level number to remove the rank from")
    async def remove_rank(self, interaction: discord.Interaction, level: int):
        """
        Remove a rank title from a given level in this guild.
        Staff/owner only.
        """
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ You must be staff or an owner to use this command.", ephemeral=True)
            return

        if level < 0 or level > 99:
            await interaction.response.send_message("❌ Level must be between 0 and 99.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        ranks_path = self._get_guild_ranks_path(guild_id)
        ranks = glob_fns().load_json(ranks_path) or {}

        level_str = str(level)
        if level_str not in ranks:
            await interaction.response.send_message(f"❌ There is no rank assigned to **Level {level}**.", ephemeral=True)
            return

        removed_rank = ranks.pop(level_str)
        glob_fns().save_json(ranks, ranks_path)

        await interaction.response.send_message(
            f"✅ Removed rank **\"{removed_rank}\"** from **Level {level}**.",
            ephemeral=False
        )

    @app_commands.command(name="set_level", description="Set a user's level directly (staff/owner only)")
    @app_commands.describe(member="The target member", level="The new level number")
    async def set_level(self, interaction: discord.Interaction, member: discord.Member, level: int):
        """
        Admin/owner command to set a user's level directly.
        The XP floor for that level is assigned automatically.
        """
        if not self._is_admin(interaction):
            await interaction.response.send_message("❌ You must be staff or an owner to use this command.", ephemeral=True)
            return

        if level < 0:
            await interaction.response.send_message("❌ Level cannot be negative.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        user_path = f"users_data/{member.id}.json"
        user_data = glob_fns().load_json(user_path)

        if user_data is None:
            await interaction.response.send_message(f"❌ {member.mention} is not registered.", ephemeral=True)
            return

        levels = self._get_levels()
        xp_for_level = levels.get(str(level), 0)

        user_data.setdefault("guild_xp", {})
        if guild_id not in user_data["guild_xp"]:
            user_data["guild_xp"][guild_id] = {"last level": 0, "xp": 0}

        user_data["guild_xp"][guild_id] = {"last level": level, "xp": xp_for_level}
        glob_fns().save_json(user_data, user_path)

        # Recalculate in case any rank titles need updating
        glob_fns().check_level_up(member.id, guild_id)

        await interaction.response.send_message(
            f"✅ Set {member.mention} to **Level {level}** with **{xp_for_level:,} XP**.",
            ephemeral=False
        )

    # ──────────────────────────────────────────────
    #  INTERNAL HELPERS
    # ──────────────────────────────────────────────

    def _is_admin(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction user has staff or owner permissions."""
        guild_data = glob_fns().load_guild(str(interaction.guild.id))
        if guild_data is None:
            return False

        user = interaction.user
        if user.id in guild_data.get("staff_person", []):
            return True
        if user.id in guild_data.get("co_owner", []):
            return True
        if user.id == guild_data.get("owner"):
            return True
        if any(r.id in guild_data.get("staff_roles", []) for r in user.roles):
            return True
        if any(r.id in guild_data.get("co_owner_roles", []) for r in user.roles):
            return True
        return False


async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))