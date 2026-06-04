import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import math
from decor import *
import asyncio
ITEMS_PER_PAGE = 5

class MarketView(View):
    def __init__(self, items, page,title):
        super().__init__()
        self.items = items
        self.page = page
        self.total_pages = math.ceil(len(items) / ITEMS_PER_PAGE)
        self.title = title
        self.previous.disabled = page == 0
        self.next.disabled = page >= self.total_pages - 1
    def get_page_embed(self):
        start = self.page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_items = self.items[start:end]

        embed = discord.Embed(
            title=f"{self.title} — Page {self.page + 1}/{self.total_pages}",
            color=discord.Color.green()
        )

        for name, details in page_items:
            embed.add_field(
                name=f"**{name}** — ₹{details['price']}",
                value=details.get("description", "No description."),
                inline=False
            )
        embed.set_footer(text="Note that the Market is subscription based! The specific balance for every item bought will be deducted, contact server adminstration for date of deduction!")

        return embed

    @discord.ui.button(label='⬅ Previous', style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        new_view = MarketView(self.items, self.page)
        await interaction.response.edit_message(embed=new_view.get_page_embed(), view=new_view)

    @discord.ui.button(label='Next ➡', style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        new_view = MarketView(self.items, self.page)
        await interaction.response.edit_message(embed=new_view.get_page_embed(), view=new_view)


class Market(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        print("Market cog registered")
    @commands.command(name="market")
    @decorators.is_channel()
    @decorators.is_user()
    async def show_market(self, ctx:commands.Context):
        try:
            with open(f"guilds_data/{ctx.guild.id}/market.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return await ctx.send(f"Error loading market: {e}")
        if not data:
            return await ctx.send("Market is currently empty.")
        items = list(data.items())  # Convert dict to list of (key, value) tuples
        view = MarketView(items, page=0,title="🛒 Market")
        embed = view.get_page_embed()
        await ctx.send(embed=embed, view=view)
    @commands.command(name="buy")
    @decorators.is_channel()
    @decorators.is_user()
    async def buy(self,ctx:commands.Context,item_name:str):
        await ctx.send("Processing your new subscription request... \nThis might take some time , please wait!")
        try:
            data = glob_fns().load_json(f"guilds_data/{ctx.guild.id}/market.json")
        except Exception as e:
            await ctx.send(f"Error loading market:{e}")
            return
        if not data:
            await ctx.send("Market is currently empty.")
            return
        if item_name not in data:
            await ctx.send("No such item exist!!!")
            return
        item = data[item_name]
        if not isinstance(item, dict) or 'price' not in item or 'role' not in item:
            await ctx.send("Invalid item format in market data.")
            return  
        if not isinstance(item['price'], int) or not isinstance(item['role'], int):
            await ctx.send("Invalid item price or role ID in market data.")
            return
        if item['price'] <= 0:
            await ctx.send("Item price must be greater than zero.")
            return
        if item['role'] <= 0:
            await ctx.send("Invalid role ID for the item.")
            return
        print(f"Item {item_name} is valid with price {item['price']} and role {item['role']}")
        if not ctx.guild.get_role(item['role']):
            await ctx.send("The role associated with this item does not exist in the server.")
            return
        user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
        user_bal = user_data['guild_balance'][str(ctx.guild.id)]
        try:
            if item['price'] > user_bal:
                return await ctx.send("Enough balance not available! \nTransaction declined")
            if item_name in user_data['subs'].get(str(ctx.guild.id), {}):
                return await ctx.send(f"Subscription for item {item_name} already exists!")
            g_log = glob_fns().load_json(f"guilds_data/{ctx.guild.id}/sub_log.json")
            g_log.setdefault(str(ctx.author.id),{})
            g_log[str(ctx.author.id)].update({str(item_name):item})
            glob_fns().save_json(g_log,f"guilds_data/{ctx.guild.id}/sub_log.json")
            role = self.bot.get_guild(ctx.guild.id).get_role(item['role'])
            await self.bot.get_guild(ctx.guild.id).get_member(ctx.author.id).add_roles(role)
            dic = {f"{ctx.guild.id}":{item_name:item}}
            user_data['subs'].update(dic)
            glob_fns().save_json(user_data,f"users_data/{ctx.author.id}.json")
            glob_fns().update_balance(str(ctx.author.id),item['price'],str(ctx.guild.id),True)
            await ctx.send("Transaction Successfull! Subscription added! \nYou can also check you currently active subscriptions with p!subs")
        except Exception as e:
            print(f"Error in buy command: {e}")
            await ctx.send(f"An error occurred while processing your purchase: {e}")
    @commands.command(name="subs")
    @decorators.is_channel()
    @decorators.is_user()
    async def subs(self,ctx:commands.Context):
        user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
        data = user_data['subs']
        if str(ctx.guild.id) not in data:
            return await ctx.send(f"{ctx.author.mention} You don't have any subscriptions yet!")
        data = data[f"{ctx.guild.id}"]
        if not data:
            return await ctx.send(f"{ctx.author.mention} You don't have any subscriptions yet!")
        items = list(data.items())  # Convert dict to list of (key, value) tuples
        view = MarketView(items, page=0,title=f"{ctx.author.display_name}'s subscriptions for {ctx.guild.name}:")
        embed = view.get_page_embed()
        embed.add_field(name="Note!",value="You can always cancle your subscription using p!cancle [item name]")
        await ctx.send(embed=embed, view=view)
    @commands.command(name="cancle")
    @decorators.is_channel()
    @decorators.is_user()
    async def cancle(self,ctx:commands.Context,item_name:str):
        user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
        if item_name not in user_data['subs'][str(ctx.guild.id)]:
            return await ctx.send("You do not have such subscription!")
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['y', 'n']
        await ctx.send(f"{ctx.author.mention} cancelling this subscription will cause you to lose related role immediately , kindly confirm the action (y/n) ")
        try:
            msg = await self.bot.wait_for('message', timeout=40.0, check=check)
            if msg.content.lower() == "n":
                return await ctx.send(f"{ctx.author.mention} that's a good decision to keep your subscription!")
            if msg.content.lower() == "y":
                g_log = glob_fns().load_json(f"guilds_data/{ctx.guild.id}/sub_log.json")
                g_log[str(ctx.author.id)].pop(item_name)
                glob_fns().save_json(g_log,f"guilds_data/{ctx.guild.id}/sub_log.json")
                user_data['subs'][str(ctx.guild.id)].pop(item_name)
                glob_fns().save_json(user_data,f"users_data/{ctx.author.id}.json")
                item_role = glob_fns().load_json(f"guilds_data/{ctx.guild.id}/market.json")[item_name]['role']
                await self.bot.get_guild(ctx.guild.id).get_member(ctx.author.id).remove_roles(self.bot.get_guild(ctx.guild.id).get_role(item_role))
                return await ctx.send(f"{ctx.author.mention} It's a good decision to cancle unnecessary subscription , a smart choice!")        
        except asyncio.TimeoutError:
            await ctx.send(f"{ctx.author.mention} you ran out of time to confirm action for cancelling your {item_name} subscription!")
        except Exception as e:
            await ctx.send(f"{ctx.author.mention} An unknown error has happened during the process , your server adminstration has been informed about it , kindly do not retry cancellation of same subscription! the role may stay for some time until our backend team looks at the issue")
            msg = f"An unknown exception has taken place when {ctx.author.display_name} tried to cancle their subscription for {item_name} , below is the error encountered: \n{e}"
            await glob_fns().critical_message_update(msg,ctx.guild.id,self.bot)
async def setup(bot:commands.Bot):
    await bot.add_cog(Market(bot))
