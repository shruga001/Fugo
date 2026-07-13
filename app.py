import discord 
from discord.ext import commands, tasks
import os
import json
from dotenv import load_dotenv
import asyncio
from datetime import datetime, timedelta
import random
from decor import decorators #custom decorators
from fns import glob_fns # custom fuunctions
from fns import *
load_dotenv()
token = os.getenv("token")
app_id = os.getenv("app_id")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='ft!',intents=intents,help_command=None)

class tasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("Tasks cog registered")
        self.monster_drop.start()

    @tasks.loop(minutes=525600)
    async def monster_drop(self):
        try:
            for discord_guild in self.bot.guilds:
                if not os.path.exists(f"guilds_data/{discord_guild.id}/config.json"):
                    continue
                guild_data = glob_fns().load_guild(str(discord_guild.id))
                if not guild_data.get("setup", False):
                    continue
                monster_channel_id = guild_data.get("monster_channel", 0)
                if monster_channel_id == 0:
                    continue
                channel = discord_guild.get_channel(monster_channel_id)
                if channel is None:
                    print(f"[{discord_guild.name}] Monster channel {monster_channel_id} missing. Notifying staff.")
                    staff_r = ""
                    for role_id in guild_data.get('staff_roles', []):
                        role = discord_guild.get_role(role_id)
                        if role:
                            staff_r += f"{role.mention} "
                    for member_id in guild_data.get('staff_person', []):
                        member = discord_guild.get_member(member_id)
                        if member:
                            staff_r += f"{member.mention} "
                    msg = f"{staff_r} this is to bring to your kind attention that bot has failed to locate the Monster drop channel. Kindly run /update_monster_channel to update new channel!"
                    await glob_fns().critical_message_update(msg, discord_guild.id, self.bot)
                    continue
                # Check last monster drop time
                last_monster = guild_data.get("last_monster")
                now = datetime.now()
                if last_monster:
                    last_monster_dt = datetime.fromisoformat(last_monster)
                    time_diff = now - last_monster_dt
                    if time_diff < timedelta(minutes=525600):
                        continue  
                guild_data["active_monster"] = True

                choice_monster = ['D'] * 30 + ['C'] * 20 + ['B'] * 15 + ['A'] * 10 + ['S'] * 5
                monsters = {
                    "D": [{
                        "name": "Slime",
                        "worth": 50,
                        "image": "https://cdn.discordapp.com/attachments/1353687961400643605/1367430526025203722/slime.PNG?ex=68148e6b&is=68133ceb&hm=2e3cf5f45ae44920a0605029e9e487b21ba04282b874be545096536199fc0fa7&"
                    }],
                    "C": [{
                        "name": "Goblin",
                        "worth": 200,
                        "image": "https://cdn.discordapp.com/attachments/1353687961400643605/1367430426221744209/goblin.png?ex=68148e53&is=68133cd3&hm=d7c463144d134d7065b5d24ec6a884afdc9bc052fa41facdea42736dc3420d5e&"
                    }],
                    "B": [{
                        "name": "Orc",
                        "worth": 500,
                        "image": "https://cdn.discordapp.com/attachments/1353687961400643605/1367430487093678111/orc.png?ex=68148e61&is=68133ce1&hm=5bc650a2322c23e77c28048542cf89fac6742786574a48ed56404ca94228c1db&"
                    }],
                    "A": [{
                        "name": "Hydra",
                        "worth": 1000,
                        "image": "https://cdn.discordapp.com/attachments/1353687961400643605/1367430460958965811/hydra.png?ex=68148e5b&is=68133cdb&hm=c7f95889f077089539334e58314e860b9a3bb931e5fbfcbcd6bd4d7fec948f17&"
                    }],
                    "S": [{
                        "name": "Dragon",
                        "worth": 5000,
                        "image": "https://cdn.discordapp.com/attachments/1353687961400643605/1367430393409704038/demonking.png?ex=68148e4b&is=68133ccb&hm=210db94d98456e400c2f45de186a9a4717467cf66aed88f82012672d4dc32485&"
                    }]
                }

                choice = random.choice(choice_monster)
                monster_data = {"rank": choice, **monsters[choice][0]}
                guild_data["current_monster"] = monster_data
                guild_data["last_monster"] = now.isoformat()

                glob_fns().save_json(guild_data, f"guilds_data/{discord_guild.id}/config.json")

                embed = discord.Embed(
                    title="A new Monster just appeared!",
                    description="Type `p!catch` to catch the monster",
                    color=discord.Color.teal()
                )
                embed.set_image(url=monster_data["image"])

                await channel.send(
                    "A monster just appeared, type `p!catch` to catch it!",
                    embed=embed
                )
        except Exception as e:
            print(f"Error in monster drop task: {e}")
            for guild in self.bot.guilds:
                try:
                    await glob_fns().critical_message_update(
                        f"An error occurred in the monster drop task: {e}",
                        guild.id,
                        self.bot
                    )
                except Exception as e2:
                    print(f"Failed to notify guild {guild.name} about the error: {e2}")
                    
    @monster_drop.before_loop
    async def before_monster_drop(self):
        await self.bot.wait_until_ready()

class misc(commands.Cog):
    def __init__(self,bot:commands.Bot):
        self.bot = bot
        print("Misc cog registered")
    @commands.command(name="catch")
    @decorators.is_user()
    async def catch(self,ctx:commands.Context):
        try:
            g_data = glob_fns().load_guild(str(ctx.guild.id))
            if ctx.channel.id != g_data['monster_channel']:
                return
            if not g_data['active_monster']:
                return await ctx.send(f"{ctx.author.mention} there is no active monster in this channel!")
            monster = g_data['current_monster']
            worth = monster['worth']
            rank = monster['rank']
            g_data['active_monster'] = False
            glob_fns().save_json(g_data,f"guilds_data/{ctx.guild.id}/config.json")
            glob_fns().update_balance(ctx.author.id,worth,ctx.guild.id,False)
            await ctx.send(f"{ctx.author.mention} just caught a monster of **rank {rank}** , **worth {worth} hill coins**")
        except Exception as e:
            print(f"Error in catch command: {e}")
            await ctx.send("An error occurred while processing your request. Please try again later.")
    @commands.command(name="Leaderboard",aliases=['lb','top'])
    @decorators.is_channel()
    @decorators.is_user()
    async def leaderboard(self,ctx:commands.Context,lb:str = None):
        if lb is None:
            with open(f"guilds_data/{ctx.guild.id}/lb.json",'r') as f:
                data = json.load(f)
            title = f"{ctx.guild.name}'s Leaderboard"
        elif lb.lower() in ['messages','msg','message','msgs']:
            with open(f"guilds_data/{ctx.guild.id}/msg.json",'r') as f:
                data = json.load(f)
            title = f"{ctx.guild.name}'s message Leaderboard"
        else:
            await ctx.send("Invalid arguments passed in leaderboard command!")
            return
        sorted_users = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        embed = discord.Embed(
            title=title,
            description="",
            color=discord.Color.pink()
            )
        for idx, (user_id, balance) in enumerate(sorted_users, start=1):
            user = bot.get_user(int(user_id))
            if not user:
                try:
                    user = await bot.fetch_user(int(user_id))
                except discord.NotFound:
                    continue
            embed.add_field(name=f"#{idx}: {user.display_name}", value=f"Balance: {balance} Hills Coins", inline=False)
        await ctx.send(embed=embed)
    @commands.command(name="rank")
    @decorators.is_channel()
    @decorators.is_user()
    async def rank(self,ctx:commands.Context,rk:str = None):
        if rk is None:
            with open(f"guilds_data/{ctx.guild.id}/lb.json",'r') as f:
                data = json.load(f)
            title = f"{ctx.author.display_name}'s rank in {ctx.guild.name}"
        elif rk.lower() in ['messages','msg','message','msgs']:
            with open(f"guilds_data/{ctx.guild.id}/msg.json",'r') as f:
                data = json.load(f)
            title = f"{ctx.author.display_name}'s message rank in {ctx.guild.name}"
        else:
            return await ctx.send("invalid argument passed!")
        sorted_users = sorted(data.items(), key=lambda x: x[1], reverse=True)
        user_rank = next((i for i, (user, _) in enumerate(sorted_users) if user == str(ctx.author.id)), -1)
        user_rank += 1  # because enumerate is 0-based
        if user_rank <= 0:
            return await ctx.send("Couldn't locate user in leaderboard!")
        embed = discord.Embed(title=title,description=f"{ctx.author.display_name} rank:",color=discord.Color.blurple())
        embed.set_thumbnail(url=f"{ctx.author.display_avatar.url}")
        embed.add_field(name=f"Rank:",value=f"{user_rank}",inline=True)
        embed.set_footer(text="tip: for msg leaderboard , try chatting in server general channels to increase your rank!")
        await ctx.send(embed=embed)
    @commands.command(name="give",aliases=['transfer','gift'])
    @decorators.is_channel()
    @decorators.is_user()
    async def give(self,ctx:commands.Context,amount:int,r_user:discord.Member):
        user_data = glob_fns().load_json(f'users_data/{ctx.author.id}.json')
        user_bal = user_data['guild_balance'][str(ctx.guild.id)]
        if r_user.bot:
            return await ctx.send(f"{ctx.author.mention} please choose a valid user!")
        if amount>user_bal:
            return await ctx.send(f"{ctx.author.mention} you do not have enough balance for this transaction!")
        if not glob_fns().user_exist(r_user,ctx.guild.id):
            return await ctx.send(f"{ctx.author.mention} \n{r_user.mention} is not registered with us!")
        glob_fns().update_balance(ctx.author.id,amount,ctx.guild.id,True)
        glob_fns().update_balance(r_user.id,amount,ctx.guild.id,False)
    @commands.command(name="bal",aliases=['balance'])
    @decorators.is_channel()
    @decorators.is_user()
    async def bal(self,ctx:commands.Context):
        user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
        user_bal = user_data['guild_balance'][str(ctx.guild.id)]
        await ctx.send(f"{ctx.author.mention} balance : {user_bal} hill coins")
    @commands.command(name="help",aliases=['commands'])
    @decorators.is_channel()
    async def help(self,ctx:commands.Context,category:str = "None",command:str="None"):
        try:
            em, embed =  glob_views().embed_view(f"help/{category}_{command}")
            if em:
                return await ctx.send(embed=embed)
            else:
                await ctx.send(f"{ctx.author.mention} no help file found for {category} {command} , try /help to see all commands")
        except Exception as e:
            print(f"Error in help command: {e}")
            await ctx.send(f"{ctx.author.mention} an error occurred while processing your request. Please try again later.")
async def main():
    await bot.add_cog(tasks(bot))
    await bot.add_cog(misc(bot))
    await bot.load_extension("guild_setup") 
    await bot.load_extension("user_setup") 
    await bot.load_extension("game") 
    await bot.load_extension("listen")
    await bot.load_extension("uno")
    await bot.load_extension("market")
    await bot.load_extension("levels")
    await bot.start(token)
# --- Kick it off ---

asyncio.run(main())
