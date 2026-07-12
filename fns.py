import json
import os
from datetime import datetime, timedelta
import discord
from discord.ext import commands


class glob_fns():
    """
    Core utility functions for the Fugo Discord bot.
    Provides data loading/saving, user management, levelling, balance,
    emoji helpers, and critical alerts.
    """

    def __init__(self):
        self.bot = None

    # --------------------------------------------------
    #  FILE I/O HELPERS
    # --------------------------------------------------

    def load_json(self, file: str):
        """Load and return JSON data from a file path. Returns None if missing."""
        if os.path.exists(file):
            with open(file, encoding="utf-8") as f:
                return json.load(f)
        print(f"⚠️ File not found: {file}")
        return None

    def save_json(self, ob, filename: str):
        """Write an object as JSON to the given file path."""
        with open(filename, 'w') as f:
            json.dump(ob, f, indent=4)
        return True

    def load_guild(self, guild_id):
        """
        Load a guild's config.json from its data directory.
        Accepts both int and str guild_id.
        """
        file = f"guilds_data/{guild_id}/config.json"
        if os.path.exists(file):
            with open(file) as f:
                return json.load(f)
        print(f"⚠️ Guild config not found: {file}")
        return None

    # --------------------------------------------------
    #  USER EXISTENCE & CREATION
    # --------------------------------------------------

    def user_exist(self, user: discord.Member, guild_id: int):
        """Check whether a user file exists and is registered in the given guild."""
        if not os.path.exists(f"users_data/{user.id}.json"):
            return False
        user_data = self.load_json(f"users_data/{user.id}.json")
        if user_data is None:
            return False
        return str(guild_id) in user_data.get('guild_balance', {}).keys()

    def create_user(self, user_id: int, guild_id: int, welcome_bonus: int = 1000):
        """
        Register a user in a guild. If the user file already exists, just
        add the new guild to their balance + XP tracking. Otherwise create
        a brand-new file from the template.
        Returns True on success, False on failure.
        """
        user_path = f"users_data/{user_id}.json"

        # ── Existing user ──────────────────────────
        if os.path.exists(user_path):
            print(f"User {user_id} already exists, updating guild balance.")
            try:
                form = self.load_json(user_path)
                if form is None:
                    return False

                # Ensure guild_balance exists
                form.setdefault("guild_balance", {})
                if str(guild_id) not in form["guild_balance"]:
                    form["guild_balance"][str(guild_id)] = 0

                # Ensure guild_xp exists
                form.setdefault("guild_xp", {})
                if str(guild_id) not in form["guild_xp"]:
                    form["guild_xp"][str(guild_id)] = {"last level": 0, "xp": 0}

                self.save_json(form, user_path)
                self.update_balance(user_id, welcome_bonus, guild_id, False)
                return True
            except Exception as e:
                print(f"❌ Error loading user data for {user_id}: {type(e).__name__}: {e}")
                return False

        # ── Brand-new user ─────────────────────────
        try:
            form = self.load_json("users_data/user_format.json")
            if form is None:
                print("❌ user_format.json template missing.")
                return False
            form["user_id"] = user_id
            form["last_login"] = datetime.now().isoformat()
            form["guild_balance"] = {str(guild_id): 0}
            form["guild_xp"] = {str(guild_id): {"last level": 0, "xp": 0}}
            self.save_json(form, user_path)
            self.update_balance(user_id, welcome_bonus, guild_id, False)
            return True
        except Exception as e:
            print(f"❌ Error creating user {user_id}: {type(e).__name__}: {e}")
            return False

    # --------------------------------------------------
    #  BALANCE / ECONOMY
    # --------------------------------------------------

    def update_balance(self, user_id: int, up_balance: int, guild_id, trea=False):
        """
        Add or subtract coins from a user's guild balance.
        When `trea=True` the amount is deducted from the user and added
        to the guild treasury.
        """
        try:
            guild_id = str(guild_id)
            user_path = f"users_data/{user_id}.json"
            guild_config_path = f"guilds_data/{guild_id}/config.json"
            lb_path = f"guilds_data/{guild_id}/lb.json"

            # ── Update user file ──────────────────────
            data = self.load_json(user_path)
            if data is None:
                return False
            data.setdefault("guild_balance", {})
            current_balance = data["guild_balance"].get(guild_id, 0)

            if not trea:
                data["guild_balance"][guild_id] = current_balance + up_balance
            else:
                data["guild_balance"][guild_id] = current_balance - up_balance

            self.save_json(data, user_path)

            # ── Treasury (only on deduction) ──────────
            if trea:
                g_data = self.load_json(guild_config_path)
                if g_data is not None:
                    g_data["treasury"] = g_data.get("treasury", 0) + up_balance
                    self.save_json(g_data, guild_config_path)

            # ── Leaderboard file ──────────────────────
            lb_data = self.load_json(lb_path)
            if lb_data is None:
                lb_data = {}

            user_key = f"{user_id}"
            lb_data.setdefault(user_key, 0)

            if not trea:
                lb_data[user_key] += up_balance
            else:
                lb_data[user_key] -= up_balance

            self.save_json(lb_data, lb_path)
            return True

        except Exception as e:
            print(f"❌ Error updating balance for user {user_id} in guild {guild_id}: {type(e).__name__}: {e}")
            return False

    # --------------------------------------------------
    #  DAILY BONUS
    # --------------------------------------------------

    def add_daily_bonus_for_user(self, user_id: int, bonus_amount: int = 500) -> str:
        """
        Grant a daily bonus of `bonus_amount` coins in every guild the user
        belongs to.  Returns a human-readable user-facing message.
        """
        try:
            path = f"users_data/{user_id}.json"
            data = self.load_json(path)
            if data is None:
                return "❌ User file not found."

            last_login = data.get("last_login")
            if not last_login:
                return "❌ No login record found."

            try:
                last_login_dt = datetime.fromisoformat(last_login)
            except ValueError:
                return "⚠️ Invalid timestamp format."

            now = datetime.now()
            time_diff = now - last_login_dt

            if time_diff >= timedelta(hours=24):
                for guild_id in data.get("guild_balance", {}).keys():
                    print(f"Adding daily bonus for user {user_id} in guild {guild_id}")
                    self.update_balance(user_id, bonus_amount, guild_id, False)

                data = self.load_json(path)          # re-read to get updated data
                data["last_login"] = now.isoformat()
                self.save_json(data, path)
                return f"✅ Daily bonus of {bonus_amount} coins added to all guilds!"
            else:
                remaining = timedelta(hours=24) - time_diff
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return (
                    f"🕒 Daily bonus already claimed. "
                    f"Try again in {remaining.days}d {hours}h {minutes}m."
                )
        except Exception as e:
            print(f"❌ Error adding daily bonus for user {user_id}: {type(e).__name__}: {e}")
            return "❌ An error occurred while processing your daily bonus."

    # --------------------------------------------------
    #  XP & LEVELLING SYSTEM
    # --------------------------------------------------

    def update_xp(self, user_id: int, up_xp: int, guild_id, trea=False):
        """
        Add XP to a user in a specific guild, then check for level-ups.
        The `trea` parameter is accepted for call-site compatibility but is
        not used by the XP system.
        """
        try:
            guild_id = str(guild_id)
            user_path = f"users_data/{user_id}.json"
            data = self.load_json(user_path)
            if data is None:
                return False

            data.setdefault("guild_xp", {})
            if guild_id not in data["guild_xp"]:
                data["guild_xp"][guild_id] = {"last level": 0, "xp": 0}

            data["guild_xp"][guild_id]["xp"] += up_xp
            self.save_json(data, user_path)

            # Check and apply any level-ups
            self.check_level_up(user_id, guild_id)
            return True

        except Exception as e:
            print(f"❌ Error updating XP for user {user_id} in guild {guild_id}: {type(e).__name__}: {e}")
            return False

    def check_level_up(self, user_id: int, guild_id):
        """
        Evaluate whether the user has crossed any XP thresholds.
        On level-up the user's stored rank is updated and True is returned.
        """
        try:
            guild_id = str(guild_id)
            user_path = f"users_data/{user_id}.json"
            data = self.load_json(user_path)
            if data is None:
                return False

            data.setdefault("guild_xp", {})
            if guild_id not in data["guild_xp"]:
                data["guild_xp"][guild_id] = {"last level": 0, "xp": 0}

            guild_data = data["guild_xp"][guild_id]
            current_xp = guild_data["xp"]
            current_level = guild_data["last level"]

            # ── Load global XP thresholds  e.g. {"1": 100, "2": 300, ...}
            levels_path = "guilds_data/guild_levels.json"
            ranks = self.load_json(levels_path)
            if ranks is None:
                print(f"⚠️ Levels file missing: {levels_path}")
                return False

            # ── Load per-guild rank titles  e.g. {"1": "Rookie", "2": "Veteran"}
            #    NOTE: The file lives at guilds_data/guild_ranks.json (shared across
            #    guilds).  Guilds that want custom rank names should create their own
            #    file at guilds_data/{guild_id}/guild_ranks.json.
            guild_ranks_path_global = "guilds_data/guild_ranks.json"
            guild_ranks_path_local = f"guilds_data/{guild_id}/guild_ranks.json"

            # Try per-guild file first, fall back to global
            if os.path.exists(guild_ranks_path_local):
                guild_ranks = self.load_json(guild_ranks_path_local) or {}
            else:
                guild_ranks = self.load_json(guild_ranks_path_global) or {}

            leveled_up = False
            while True:
                next_level = str(current_level + 1)
                if next_level not in ranks:
                    break
                required_xp = ranks[next_level]
                if current_xp >= required_xp:
                    current_level += 1
                    leveled_up = True
                    # Assign rank title if one exists for this level
                    if next_level in guild_ranks:
                        data.setdefault("guild_ranks", {})
                        data["guild_ranks"][guild_id] = guild_ranks[next_level]
                else:
                    break

            guild_data["last level"] = current_level
            self.save_json(data, user_path)
            return leveled_up

        except Exception as e:
            print(f"❌ Error checking level up for user {user_id} in guild {guild_id}: {type(e).__name__}: {e}")
            return False

    # --------------------------------------------------
    #  EMOJI HELPERS
    # --------------------------------------------------

    def get_emoji(self, name: str, file: str) -> str:
        """
        Resolve an emoji name to its Discord mention string using
        the corresponding emoji_data_{file}.json.
        """
        try:
            if file != "blackj":
                name = name.lower()
            file = file.lower()
            with open(f"emojis/emoji_data_{file}.json", "r") as f:
                emojis = json.load(f)
            emoji_data = emojis[str(name)]
            if emoji_data.get("animated", False):
                return f"<a:{emoji_data['name']}:{emoji_data['id']}>"
            else:
                return f"<:{emoji_data['name']}:{emoji_data['id']}>"
        except FileNotFoundError:
            print(f"⚠️ emoji_data_{file}.json not found.")
            return "❓"
        except KeyError:
            print(f"⚠️ Emoji '{name}' not found in emoji_data_{file}.json.")
            return "❓"
        except Exception as e:
            print(f"⚠️ Unexpected error in get_emoji: {e}")
            return "❓"

    # --------------------------------------------------
    #  CRITICAL ALERTS
    # --------------------------------------------------

    async def critical_message_update(self, msg: str, guild_id: int, bot: commands.Bot):
        """
        Send a critical notification to the guild's critical-update channel.
        If the channel is inaccessible the message is forwarded to the guild
        owner and all co-owners.
        """
        guild_data = self.load_guild(guild_id)
        if guild_data is None:
            print(f"⚠️ critical_message_update: no config for guild {guild_id}")
            return

        critical_channel = bot.get_channel(guild_data.get('critical_update_channel'))
        if critical_channel:
            await critical_channel.send(msg)
        else:
            full_msg = (
                msg + "\n\nIn addition to the above information, the critical update "
                "channel is also not accessible. Kindly verify that the bot has proper "
                "access to the channel and that the channel exists. In case the channel "
                "has been deleted, kindly create a new channel and update it in bot "
                "configuration using `/set_critical_update_channel`."
            )
            guild = bot.get_guild(int(guild_id))
            if guild:
                await guild.owner.send(full_msg)
                for co_id in guild_data.get('co_owner', []):
                    co_owner = guild.get_member(co_id)
                    if co_owner:
                        await co_owner.send(full_msg)


class glob_views():
    """
    Provides Discord embed views constructed from JSON definitions stored
    inside guilds_data/help/.
    """

    def __init__(self):
        pass

    def embed_view(self, embed_id: str):
        """
        Load a JSON embed definition and return a discord.Embed object.
        Returns (True, embed) on success or (False, error) on failure.
        """
        try:
            embed_info = glob_fns().load_json(f"guilds_data/{embed_id}.json")
        except Exception as e:
            return False, e

        if embed_info is None:
            return False, f"Embed file not found: guilds_data/{embed_id}.json"

        embed = discord.Embed(
            title=embed_info.get('Title', 'No Title'),
            description=embed_info.get('Description', ''),
            color=embed_info.get('color', discord.Color.default())
        )

        for field in embed_info.get('fields', []):
            embed.add_field(
                name=field.get('Title', ''),
                value=field.get('Value', ''),
                inline=bool(field.get('inline', False))
            )
        return True, embed