from discord.ext import commands
from decor import *
from fns import *
from datetime import datetime,timedelta
class user_setup(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        print("User data cog registered")
    @commands.command(name="reg")
    @decorators.is_channel()
    async def reg(self,ctx:commands.Context):
        print(f"User {ctx.author.name} ({ctx.author.id}) is trying to register for guild {ctx.guild.name} ({ctx.guild.id})")
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        print(f"User {ctx.author.name} ({user_id}) is trying to register for guild {ctx.guild.name} ({guild_id})")
        if glob_fns().create_user(user_id=user_id,guild_id=guild_id):
            await ctx.send(f"{ctx.author.mention} successfully registered! for guild \"{ctx.guild.name}\" ")
        else:
            await ctx.send(f"{ctx.author.mention} there was an issue to get you registered for guild \"{ctx.guild.name}\"")
    @commands.command(name="daily",aliases=['collect'])
    @decorators.is_user()
    @decorators.is_channel()
    async def daily(self,ctx:commands.Context):
        user_id = ctx.author.id
        msg = glob_fns().add_daily_bonus_for_user(user_id)
        await ctx.send(f"{ctx.author.mention} {msg}")
async def setup(bot:commands.Bot):
    await bot.add_cog(user_setup(bot))