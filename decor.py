from discord.ext import commands
import os
from fns import *
from discord import app_commands
class decorators:
    @staticmethod
    def is_channel():
        async def predicate(ctx: commands.Context):
            if ctx.guild is None:
                await ctx.send("This command can only be used in a server.")
                return False
            path = f"guilds_data/{ctx.guild.id}/config.json"
            if not os.path.exists(path):
                await ctx.send("The bot is not yet setup! Please run /setup to configure the bot.")
                return False

            guild_data = glob_fns().load_guild(ctx.guild.id)
            if not guild_data.get("setup"):
                await ctx.send("The bot is not yet setup! Please complete the setup.")
                return False

            allowed_channels = guild_data.get("allowed_channels", [])
            if ctx.channel.id not in allowed_channels:
                await ctx.send(f"{ctx.author.mention}, please use the bot in its allowed channel.")
                return False
            return True
        return commands.check(predicate)

    def is_user():
        async def predicate(ctx: commands.Context):
            path = f"users_data/{ctx.author.id}.json"
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                if str(ctx.guild.id) in data.get('guild_balance', {}):
                    return True
            await ctx.send("Type `p!start` to open your Fugo account and start earning!")
            return False
        return commands.check(predicate)
    def is_staff():
        async def predicate(interaction : discord.interactions):
            ctx = interaction
            guild_data = glob_fns().load_guild(ctx.guild.id)
            if ctx.user.id in guild_data['staff_person']:
                return True
            elif any(role.id in guild_data['staff_roles'] for role in interaction.user.roles):
                return True
            await interaction.response.send_message("You must be a valid staff member in order to run this command")
        return app_commands.check(predicate)
    def is_owner():
        async def predicate(interaction : discord.interactions):
            ctx = interaction
            guild_data = glob_fns().load_guild(ctx.guild.id)
            if ctx.user.id in guild_data['co_owner']:
                return True
            elif any(role.id in guild_data['co_owner_roles'] for role in interaction.user.roles):
                return True
            await interaction.response.send_message("You must be a valid Owner or co-owner in order to run this command")
        return app_commands.check(predicate)