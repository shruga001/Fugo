import json
import os
from datetime import datetime, timedelta
import discord
from discord.ext import commands


class glob_fns():
    def __init__(self):
        self.bot = None  # FIX 1: was a local variable, not an instance attribute

    def user_exist(self, user: discord.Member, guild_id: int):
        # FIX 2: removed redundant double os.path.exists check
        if not os.path.exists(f"users_data/{user.id}.json"):
            return False
        user_data = self.load_json(f"users_data/{user.id}.json")
        return str(guild_id) in user_data['guild_balance'].keys()

    async def critical_message_update(self, msg: str, guild_id: int, bot: commands.Bot):
        guild_data = self.load_guild(guild_id=guild_id)
        critical_channel = bot.get_channel(guild_data['critical_update_channel'])
        if critical_channel:
            await critical_channel.send(msg)
        else:
            msg = (
                msg + "\nIn addition to the above given information, the critical update "
                "channel is also not accessible. Kindly verify that the bot has proper "
                "access to the channel and that the channel exists. In case the channel "
                "has been deleted, kindly create a new channel and update it in bot "
                "configuration using /set_criticial_update_channel"
            )
            guild = bot.get_guild(guild_id)
            await guild.owner.send(msg)
            for co in guild_data['co_owner']:
                coowner = guild.get_member(co)
                await coowner.send(msg)

    def get_emoji(self, name: str, file):
        try:
            if file != "blackj":
                name = name.lower()
            file = file.lower()
            with open(f"emojis/emoji_data_{file}.json", "r") as f:
                emojis = json.load(f)
            emoji_data = emojis[str(name)]
            if emoji_data.get("animated", False):
                emoji_call = f"<a:{emoji_data['name']}:{emoji_data['id']}>"
            else:
                emoji_call = f"<:{emoji_data['name']}:{emoji_data['id']}>"
            return emoji_call
        except FileNotFoundError:
            print(f"⚠️ emoji_data_{file}.json not found.")
            return "❓"
        except KeyError:
            print(f"⚠️ Emoji '{name}' not found in emoji_data_{file}.json.")
            return "❓"
        except Exception as e:
            print(f"⚠️ Unexpected error in get_emoji: {e}")
            return "❓"

    def add_daily_bonus_for_user(self, user_id: int) -> str:
        try:
            path = f"users_data/{user_id}.json"
            if not os.path.exists(path):
                return "❌ User file not found."
            with open(path, "r") as f:
                data = json.load(f)
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
                    self.update_balance(user_id, 500, guild_id, False)
                data = self.load_json(path)
                data["last_login"] = now.isoformat()
                with open(path, "w") as f:
                    json.dump(data, f, indent=4)
                return "✅ Daily bonus of 500 coins added to all guilds!"
            else:
                remaining = timedelta(hours=24) - time_diff
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return f"🕒 Daily bonus already claimed. Try again in {remaining.days}d {hours}h {minutes}m."
        except Exception as e:
            print(f"❌ Error adding daily bonus for user {user_id}: {type(e).__name__}: {e}")
            return "❌ An error occurred while processing your daily bonus."

    def load_json(self, file):
        if os.path.exists(file):
            with open(file, encoding="utf-8") as f:
                return json.load(f)

    def load_guild(self, guild_id):
        file = f"guilds_data/{guild_id}/config.json"
        if os.path.exists(file):
            with open(file) as f:
                return json.load(f)

    def check_level_up(self, user_id: int, guild_id: int):
        try:
            user_path = f"users_data/{user_id}.json"
            with open(user_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            guild_id = str(guild_id)
            data.setdefault("guild_xp", {})

            if guild_id not in data["guild_xp"]:
                data["guild_xp"][guild_id] = {"last level": 0, "xp": 0}

            guild_data = data["guild_xp"][guild_id]
            current_xp = guild_data["xp"]
            current_level = guild_data["last level"]

            # Load XP thresholds per level e.g. {"1": 100, "2": 300, ...}
            with open("guilds_data/guild_levels.json", "r", encoding="utf-8") as f:
                ranks = json.load(f)

            # FIX 3: Load guild ranks separately with its own handle
            # e.g. {"1": "Rookie", "2": "Veteran", ...}
            guild_ranks_path = f"guilds_data/{guild_id}/guild_ranks.json"
            with open(guild_ranks_path, "r", encoding="utf-8") as r:
                guild_ranks = json.load(r)

            leveled_up = False
            while True:
                next_level = str(current_level + 1)
                if next_level not in ranks:
                    break
                required_xp = ranks[next_level]
                if current_xp >= required_xp:
                    current_level += 1
                    leveled_up = True
                    # Assign rank reward to user if one is defined for this level
                    if next_level in guild_ranks:
                        data.setdefault("guild_ranks", {})
                        data["guild_ranks"][guild_id] = guild_ranks[next_level]
                else:
                    break

            guild_data["last level"] = current_level
            with open(user_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            return leveled_up

        except Exception as e:
            print(
                f"❌ Error checking level up for user {user_id} "
                f"in guild {guild_id}: {type(e).__name__}: {e}"
            )

    def update_xp(self, user_id: int, up_xp: int, guild_id: int):
        # FIX 4: removed unused `trea` parameter
        try:
            user_path = f"users_data/{user_id}.json"
            with open(user_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            data.setdefault("guild_xp", {})
            guild_id = str(guild_id)

            if guild_id not in data["guild_xp"]:
                data["guild_xp"][guild_id] = {"last level": 0, "xp": 0}

            data["guild_xp"][guild_id]["xp"] += up_xp

            with open(user_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            self.check_level_up(user_id, guild_id)
            return True

        except Exception as e:
            print(
                f"❌ Error updating XP for user {user_id} in guild {guild_id}: "
                f"{type(e).__name__}: {e}"
            )
            return False

    def update_balance(self, user_id: int, up_balance: int, guild_id: int, trea=False):
        try:
            user_path = f"users_data/{user_id}.json"
            guild_path = f"guilds_data/{guild_id}/config.json"

            with open(user_path, "r") as f:
                data = json.load(f)

            data.setdefault("guild_balance", {})
            current_balance = data["guild_balance"].get(str(guild_id), 0)

            if not trea:
                data["guild_balance"][str(guild_id)] = current_balance + up_balance
            else:
                data["guild_balance"][str(guild_id)] = current_balance - up_balance

            with open(user_path, "w") as f:
                json.dump(data, f, indent=4)

            if trea:
                with open(guild_path, "r") as f:
                    g_data = json.load(f)
                g_data["treasury"] = g_data.get("treasury", 0) + up_balance
                with open(guild_path, "w") as f:
                    json.dump(g_data, f, indent=4)

            with open(f"guilds_data/{guild_id}/lb.json", "r") as f:
                g_data = json.load(f)

            g_data.setdefault(f"{user_id}", 0)

            # FIX 5: changed to if/else instead of two separate if checks
            if not trea:
                g_data[f"{user_id}"] += up_balance
            else:
                g_data[f"{user_id}"] -= up_balance

            with open(f"guilds_data/{guild_id}/lb.json", "w") as f:
                json.dump(g_data, f, indent=4)

        except Exception as e:
            print(f"❌ Error updating balance for user {user_id} in guild {guild_id}: {type(e).__name__}: {e}")
            return False

    def create_user(self, user_id: int, guild_id: int):
        if os.path.exists(f'users_data/{user_id}.json'):
            print(f"User {user_id} already exists, updating guild balance.")
            try:
                with open(f"users_data/{user_id}.json", "r") as f:
                    form = json.load(f)
                if str(guild_id) not in form["guild_balance"]:
                    form["guild_balance"][str(guild_id)] = 0
                    # FIX 6: use correct dict structure instead of integer 0
                    form["guild_xp"][str(guild_id)] = {"last level": 0, "xp": 0}
                    with open(f"users_data/{user_id}.json", "w") as f:
                        json.dump(form, f, indent=4)
                    self.update_balance(user_id, 1000, guild_id, False)
                return True
            except Exception as e:
                print(f"❌ Error loading user data for {user_id}: {type(e).__name__}: {e}")
                return False
        else:
            # FIX 7: fixed indentation — file write and update_balance are inside else
            with open("users_data/user_format.json", "r") as f:
                form = json.load(f)
            form["user_id"] = user_id
            form["last_login"] = datetime.now().isoformat()
            form["guild_balance"] = {str(guild_id): 0}
            # FIX 6b: initialise guild_xp properly for brand new users too
            form["guild_xp"] = {str(guild_id): {"last level": 0, "xp": 0}}
            with open(f"users_data/{user_id}.json", "w") as f:
                json.dump(form, f, indent=4)
            self.update_balance(user_id, 1000, guild_id, False)
            return True

    def save_json(self, ob, filename):
        with open(filename, 'w') as f:
            json.dump(ob, f, indent=4)
        return True


class glob_views():
    def __init__(self):
        pass

    def embed_view(self, embed_id):
        try:
            embed_info = glob_fns().load_json(f"guilds_data/{embed_id}.json")
        except Exception as e:
            return False, e

        embed = discord.Embed(
            title=embed_info['Title'],
            description=embed_info['Description'],
            color=embed_info['color']
        )

        # FIX 8: renamed loop variable from embed_info to field to avoid shadowing
        for field in embed_info['fields']:
            embed.add_field(
                name=field['Title'],
                value=field['Value'],
                inline=bool(field['inline'])
            )
        return True, embed