from fns import *
import discord
import os
from discord.ext import commands
import random
class Listeners(commands.Cog):
    def __init__(self,bot:commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        activity = discord.Game(name="in the hills with my nakamas!")
        await self.bot.change_presence(status=discord.Status.online, activity=activity)
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot or not message.guild:
                return
            guild_id = str(message.guild.id)
            user_id = str(message.author.id)
            if not os.path.exists(f"guilds_data/{guild_id}/config.json"):
                return
            if not glob_fns().user_exist(message.author, message.guild.id):
                return
            guild = glob_fns().load_guild(guild_id)
            if not guild.get("setup"):
                return
            if message.channel.id not in guild.get("message_channels", []):
                return
            if len(str(message.content.strip())) < 10:
                return
            with open(f"guilds_data/{message.guild.id}/msg.json",'r') as f:
                gm_data = json.load(f)
            gm_data.setdefault(f"{message.author.id}",0)
            gm_data[f"{message.author.id}"] += 1
            glob_fns().save_json(gm_data, f"guilds_data/{guild_id}/msg.json")
            coins = [5,10,15,20,25,30,35,40,45,50]
            coin = random.choice(coins)
            glob_fns().update_balance(message.author.id,coin,message.guild.id,False)
            glob_fns().update_xp(message.author.id,coin,message.guild.id,False)
        except Exception as e:
            print(f"Error in on_message listener: {e}")
        await self.bot.process_commands(message)
    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        if guild.system_channel: 
            await guild.system_channel.send(f'Thanks for inviting me to {guild.name}, I am fugo , developed with love and care from my developer ***Shruga_001***, to get started please start the command /setup')
        else:
            await guild.owner.send(f'Thanks for inviting me to {guild.name}, I am fugo , developed with love and care from my developer ***Shruga_001***, to get started please start the command /setup')
async def setup(bot:commands.Bot):
    await bot.add_cog(Listeners(bot))


