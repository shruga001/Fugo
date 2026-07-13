from discord.ext import commands
from decor import decorators
from fns import *
import asyncio
from blackj import *
import random
import rps
from tnd import *
from discord.ui import View
import discord         
class blackjbut(View):
    # I do not have a timeout for this view,  I need to add a timeout to prevent the buttons from being active indefinitely.

    def __init__(self, *, timeout = None,game:Blackjackclass,ctx:commands.Context):
        super().__init__(timeout=timeout)
        self.game = game
        self.ctx = ctx
        self.message = None
    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        try:
            await self.message.edit(view=self)
        except:
            pass
    async def declare_result(self, result: str):
        embed = discord.Embed(title=f"{self.ctx.author.name} Blackjack Result",description="We have a result for the game",color=discord.Colour.magenta())
        embed.add_field(name=f"{self.ctx.author.name} Hand:" , 
                        value=f"Cards drawn: {''.join(glob_fns().get_emoji(card,'blackj') for card in self.game.user_hand)} \nCards Value: {self.game.user_value}")
        embed.add_field(name="Dealer Hand:",
                        value=f"Cards drawn: {''.join(glob_fns().get_emoji(card,'blackj') for card in self.game.bot_hand)} \nCards Value: {self.game.bot_value}",inline=False)
        embed.add_field(name="Final result:",value=f"***{result}*** \nbid placed - {self.game.bet} hill coins",inline=False)
        embed.set_image(url="https://clientarea.evolution.com/netent/wp-content/nfs-uploads/uploads/cdn/3b662a4ba2d3f74dc7e050836523a6f6/02_banner_blackjack_720x300_blackjackhtml5.jpg")
        embed.set_footer(text="If you feel like there is any fault in the game above , feel free to contact our backend team via your server adminstration.")
        await self.ctx.send(f"{self.ctx.author.mention}",embed=embed)
        self.stop()
    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self,interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.game.user_id:
                await interaction.response.send_message(f"{interaction.user.mention} You are not the player of this game!", ephemeral=True)
                return
            await interaction.response.defer()
            if not self.game:
                await self.ctx.send(f"{interaction.user.mention} No active game found!")
                return
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            await interaction.message.edit(view=self)
            self.game.draw()
            if self.game.user_value > 21:
                result = self.game.check_result(self.ctx.guild.id)
                await self.declare_result(result)
                self.stop()
                return
            new_card = self.game.user_hand[-1]
            new_card = glob_fns().get_emoji(new_card,"blackj")
            embed = discord.Embed(title=f"{self.ctx.author.name} Blackjack Game", description="You drew a card!", color=discord.Color.magenta())
            embed.add_field(name="Card drawn", value=f"{new_card}", inline=False)
            embed.add_field(name="Your Hand Value", value=f"{self.game.user_value}", inline=False)
            await self.ctx.send(f"{self.ctx.author.mention}", embed=embed,view=blackjbut(timeout=None,game=self.game,ctx=self.ctx))
            v = self
            await interaction.followup.edit_message(message_id=interaction.message.id,view=v)
        except Exception as e:
            print(f"❌ Error in hit button: {type(e).__name__}: {e}")
            await interaction.response.send_message(f"An error occurred while processing your request: {e}", ephemeral=True)
        finally:
            self.stop()
    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message(f"{interaction.user.mention} You are not the player of this game!", ephemeral=True)
            return
        await interaction.response.defer()
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if not self.game:
            await self.ctx.send(f"{interaction.user.mention} No active game found!")
            return
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message(f"{interaction.user.mention} You are not the player of this game!", ephemeral=True)
            return
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        # Update the message
        await interaction.message.edit(view=self)
        # Optionally respond to the interaction
        result = self.game.check_result(self.ctx.guild.id)
        await self.declare_result(result)
        v = self
        await interaction.followup.edit_message(message_id=interaction.message.id,view=v)
        self.stop()
class games(commands.Cog):
    def __init__(self,bot:commands.Bot):
        self.bot = bot
        print("Games cog registered")
    @commands.command(name="blackjack",aliases=["bj"])
    @decorators.is_channel()
    @decorators.is_user()
    async def blackjack(self,ctx:commands.Context,bid:str):
        user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
        user_bal = user_data['guild_balance'][f"{ctx.guild.id}"]
        if user_bal <= 0:
            await ctx.send(f"{ctx.author.mention} There was a random glitch in the bot! , we are deeply sorry for the error! \nHere is 5 times hill coins of your current balance \ncalculating new balance...")
            await asyncio.sleep(3)
            await ctx.send(f"{ctx.author.mention} I ran some rocket science level calculations but still I couldnt increase your balance above {5 * user_bal} coins because you never had any positive balance....")
            return
        if bid.lower() == "all":
            bid = user_bal
        elif not bid.isdigit():
            await ctx.send(f"{ctx.author.mention} bid must be an integer or all!")
            return
        bid = int(bid)
        if bid>10000:
            await ctx.send(f"{ctx.author.mention} bid is limited to 10,000! continuing game with 10,000 coins")
            bid = 10000
        if bid<=0:
            await ctx.send(f"{ctx.author.mention} There was a random glitch in the bot! , we are deeply sorry for the error! \nHere is 5 times hill coins of your current balance \ncalculating new balance...")
            await asyncio.sleep(3)
            await ctx.send(f"{ctx.author.mention} I ran some rocket science level calculations but still I couldnt increase your balance above {5 * user_bal} coins because you never had any positive balance....")
            return
        if bid>user_bal:
            await ctx.send(f"{ctx.author.mention} Trying to bid bigger than your pocket? \nBid placed:{bid} \nUser Balance:{user_bal}")
            return
        if bid>10000:
                await ctx.send(f"{ctx.author.mention} bid is limited to 10,000! continuing lottery with 10,000 coins")
                bid = 10000
        await ctx.send(f"{ctx.author.mention} Starting a game of Blackjack with a bid of {bid} coins")
        game = Blackjackclass(ctx.author.id,bid)
        game.create_deck()
        game.pick_hand()
        await ctx.send("Let the magic of Blackjack begin!")
        await ctx.send("Shuffling cards!!!")
        await asyncio.sleep(2)
        await ctx.send("Distributing cards")
        await asyncio.sleep(2)
        bj_user = game.is_blackjack(game.user_hand)
        if len(game.bot_hand) ==2:
            bj_dealer = game.is_blackjack(game.bot_hand)
        else:
            bj_dealer = False
        if bj_user and bj_dealer:
            await ctx.send(f"{ctx.author.mention} You both got blackjack! it's a tie 🤝")
            return
        elif bj_user and not bj_dealer:
            glob_fns().update_balance(ctx.author.id,game.bet,ctx.guild.id,False)
            await ctx.send(f"{ctx.author.mention} You won with Blackjack! 🎉")
            return
        elif bj_dealer:
            glob_fns().update_balance(ctx.author.id,game.bet,ctx.guild.id,True)
            await ctx.send(f"{ctx.author.mention} Dealer won with Blackjack! 🎃")
            return
        user_hands_raw = game.user_hand
        user_hands = ""
        for hand in user_hands_raw:
            user_hands += " " + glob_fns().get_emoji(hand,"blackj")
        await asyncio.sleep(1)
        embed = discord.Embed(title=f"{ctx.author.name} Blackjack Game", description="Your hand is ready!", color=discord.Color.magenta())
        embed.add_field(name="Your Hand", value=user_hands, inline=False)
        embed.add_field(name="Your Hand Value", value=game.user_value, inline=False)
        dealer_hand_raw = game.bot_hand
        dealer_hand = ""
        for hand in dealer_hand_raw[:-1]:
            dealer_hand += " "+glob_fns().get_emoji(hand,"blackj")
        embed.add_field(name="Dealer's Hand", value=dealer_hand, inline=False)
        embed.add_field(name="Dealer's Hand Value", value="unknown", inline=False)
        embed.set_footer(text="You can hit or stand using the buttons below")
        view_bj = blackjbut(timeout=120,game=game,ctx=ctx)
        view_bj.message = await ctx.send(f"{ctx.author.mention}",embed=embed,view=view_bj)

    @blackjack.error
    async def blackjack_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide a bid amount. Example: `p!blackjack 500`")
    @commands.command()
    async def giverole(self,ctx, role_id: int):
        role = ctx.guild.get_role(role_id)
        if role is None:
            await ctx.send("Role not found.")
            return

        try:
            await ctx.author.add_roles(role)
            await ctx.send(f"✅ You have been given the role: {role.name}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to assign that role.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.command(name="bet",aliases=["snakeeyes",'snake','roll'])
    @decorators.is_channel()
    @decorators.is_user()
    async def bet(self,ctx:commands.Context,bid:str):
        try:
            user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
            user_bal = user_data['guild_balance'][f"{ctx.guild.id}"]
            if user_bal <= 0:
                await ctx.send(f"{ctx.author.mention} There was a random glitch in the bot! , we are deeply sorry for the error! \nHere is 5 times hill coins of your current balance \ncalculating new balance...")
                await asyncio.sleep(3)
                await ctx.send(f"{ctx.author.mention} I ran some rocket science level calculations but still I couldnt increase your balance above {5 * user_bal} coins because you never had any positive balance....")
                return
            if bid.lower() == "all":
                bid = user_bal
            elif not bid.isdigit():
                await ctx.send(f"{ctx.author.mention} bid must be an integer or all!")
                return
            bid = int(bid)
            if bid>10000:
                await ctx.send(f"{ctx.author.mention} bid is limited to 10,000! continuing game with 10,000 coins")
                bid = 10000
            if bid<=0:
                await ctx.send(f"{ctx.author.mention} There was a random glitch in the bot! , we are deeply sorry for the error! \nHere is 5 times hill coins of your current balance \ncalculating new balance...")
                await asyncio.sleep(3)
                await ctx.send(f"{ctx.author.mention} I ran some rocket science level calculations but still I couldnt increase your balance above {5 * user_bal} coins because you never had any positive balance....")
                return
            if bid>user_bal:
                await ctx.send(f"{ctx.author.mention} Trying to bid bigger than your pocket? \nBid placed:{bid} \nUser Balance:{user_bal}")
                return
            if bid>10000:
                    await ctx.send(f"{ctx.author.mention} bid is limited to 10,000! continuing lottery with 10,000 coins")
                    bid = 10000
            await ctx.send(f"{ctx.author.mention} Rolling dice : {glob_fns().get_emoji('dice_roll','roll')}")
            await asyncio.sleep(3)
            dice1 = random.randrange(1,6)
            dice2 = random.randrange(1,6)
            await ctx.send("And the dice rolls:")
            await asyncio.sleep(1)
            await ctx.send(f"Dice 1 : {glob_fns().get_emoji(f'Dice_{dice1}','roll')}")
            await asyncio.sleep(2)
            await ctx.send(f"Dice 2 : {glob_fns().get_emoji(f'Dice_{dice2}','roll')}")
            if dice1==1 or dice2 ==1:
                if dice2 ==1 and dice1==1:
                    glob_fns().update_balance(ctx.author.id,5*bid,ctx.guild.id,False)
                    await ctx.send(f"{ctx.author.mention} just won 5x of their bid in snake-eyes")
                else:
                    glob_fns().update_balance(ctx.author.id,2*bid,ctx.guild.id,False)
                    await ctx.send(f"{ctx.author.mention} just won 2x of their bid in snake-eyes")
            else:
                glob_fns().update_balance(ctx.author.id,bid,ctx.guild.id,True)
                await ctx.send(f"{ctx.author.mention} just lost {bid} in snake-eyes")
            user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
            user_bal_up = user_data['guild_balance'][f"{ctx.guild.id}"]
            embed = discord.Embed(title="Snake eyes result...",color=discord.Color.dark_green())
            embed.add_field(name="Dice rolls",value=f"Dice 1 : {glob_fns().get_emoji(f'Dice_{dice1}','roll')} \nDice 2 : {glob_fns().get_emoji(f'Dice_{dice2}','roll')}")
            embed.add_field(name="Result", value=f"Bid - {bid} hill coins \nOriginal Balance - {user_bal} hill coins \nUpdated new balance : {user_bal_up} hill coins")
            embed.set_image(url="https://i.pinimg.com/736x/2b/43/97/2b4397e8e5abcbdaf8d63efc6ba52c7f.jpg")
            await ctx.send(f"{ctx.author.mention}",embed=embed)
        except Exception as e:
            print(f"❌ Error in bet command: {type(e).__name__}: {e}")
            await ctx.send(f"An error occurred while processing your bet: {e}")
    @bet.error
    async def bet_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide a bid amount. Example: `p!bet 500`")
    @commands.command(name="rps")
    @decorators.is_channel()
    @decorators.is_user()
    async def rps(self,ctx:commands.Context,bid:str,opponent:discord.Member = None):
        user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
        user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
        user_bal = user_data['guild_balance'][f"{ctx.guild.id}"]
        if user_bal <= 0:
            await ctx.send(f"{ctx.author.mention} There was a random glitch in the bot! , we are deeply sorry for the error! \nHere is 5 times hill coins of your current balance \ncalculating new balance...")
            await asyncio.sleep(3)
            await ctx.send(f"{ctx.author.mention} I ran some rocket science level calculations but still I couldnt increase your balance above {5 * user_bal} coins because you never had any positive balance....")
            return
        if bid.lower() == "all":
            bid = user_bal
        elif not bid.isdigit():
            await ctx.send(f"{ctx.author.mention} bid must be an integer or all!")
            return
        bid = int(bid)
        if bid>1000:
            await ctx.send(f"{ctx.author.mention} bid is limited to 1,000! continuing game with 1,000 coins")
            bid = 1000
        if bid<=0:
            await ctx.send(f"{ctx.author.mention} There was a random glitch in the bot! , we are deeply sorry for the error! \nHere is 5 times hill coins of your current balance \ncalculating new balance...")
            await asyncio.sleep(3)
            await ctx.send(f"{ctx.author.mention} I ran some rocket science level calculations but still I couldnt increase your balance above {5 * user_bal} coins because you never had any positive balance....")
            return
        if bid>user_bal:
            await ctx.send(f"{ctx.author.mention} Trying to bid bigger than your pocket? \nBid placed:{bid} \nUser Balance:{user_bal}")
            return
        if opponent is None:
            game = rps.RPSChallengeBot(ctx.author,ctx.guild.id,ctx,bid)
            await game.send_prompt()
            return
        if opponent.bot or opponent == ctx.author:
            await ctx.send("Please bet against someone real")
            return
        if not glob_fns().user_exist(opponent,ctx.guild.id):
            return await ctx.send(f"{ctx.author.mention} \n{opponent.mention} is not registered with us!")
        opponent_data = glob_fns().load_json(f"users_data/{opponent.id}.json")
        opp_bal = opponent_data['guild_balance'][f'{ctx.guild.id}']
        if opp_bal < bid:
            await ctx.send(f"for game between {ctx.author.mention} & {opponent.mention} , {opponent.mention} does not have enough bid")
            return
        game = rps.RPSChallenge(ctx,ctx.author,opponent,bid,ctx.guild.id)
        await game.send_choices()
    @rps.error
    async def rps_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide a bid amount. Example: `!rps 500`")
    @commands.command(name="fish")
    @decorators.is_channel()
    @decorators.is_user()
    @commands.cooldown(1,300,commands.BucketType.user)
    async def fish(self,ctx:commands.Context):
        fish_outcomes = [
        ("nothing", 0, 20),
        ("d", 50, 50),
        ("c", 100, 20),
        ("b", 500, 7),
        ("a", 1000, 3),
        ("s", 5000, 1)
        ]
        # Ensure fish dict has all keys initialized
        roll = random.randint(1, 100)
        cumulative = 0
        result = None
        for fish_type, reward, chance in fish_outcomes:
            cumulative += chance
            if roll <= cumulative:
                result = (fish_type, reward)
                break
        if result[0] == "nothing":
            await ctx.send(f"{ctx.author.mention}, you went fishing but caught nothing. Maybe next time!")
        else:
            glob_fns().update_balance(ctx.author.id,result[1],ctx.guild.id,False)
            await ctx.send(f"{ctx.author.mention}, you caught a class {result[0].replace('_', ' ').title()} worth {result[1]} Hills Coins! the respective coins have been added to your account")
    @fish.error
    async def fish_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(int(error.retry_after), 60)
            await ctx.send(f"Please wait {minutes} minutes and {seconds} seconds before fishing again.")
    @commands.command(name="lottery")
    @decorators.is_channel()
    @decorators.is_user()
    async def lottery(self,ctx:commands.Context,bid:str):
        try:
            user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
            user_data = glob_fns().load_json(f"users_data/{ctx.author.id}.json")
            user_bal = user_data['guild_balance'][f"{ctx.guild.id}"]
            if user_bal <= 0:
                await ctx.send(f"{ctx.author.mention} There was a random glitch in the bot! , we are deeply sorry for the error! \nHere is 5 times hill coins of your current balance \ncalculating new balance...")
                await asyncio.sleep(3)
                await ctx.send(f"{ctx.author.mention} I ran some rocket science level calculations but still I couldnt increase your balance above {5 * user_bal} coins because you never had any positive balance....")
                return
            if bid.lower() == "all":
                bid = user_bal
                if bid>200:
                    await ctx.send(f"{ctx.author.mention} bid is limited to 200! continuing lottery with 200 coins")
                    bid = 200
            elif not bid.isdigit():
                await ctx.send(f"{ctx.author.mention} bid must be an integer or all!")
                return
            bid = int(bid)
            if bid<=0:
                await ctx.send(f"{ctx.author.mention} There was a random glitch in the bot! , we are deeply sorry for the error! \nHere is 5 times hill coins of your current balance \ncalculating new balance...")
                await asyncio.sleep(3)
                await ctx.send(f"{ctx.author.mention} I ran some rocket science level calculations but still I couldnt increase your balance above {5 * user_bal} coins because you never had any positive balance....")
                return
            if bid>user_bal:
                await ctx.send(f"{ctx.author.mention} Trying to bid bigger than your pocket? \nBid placed:{bid} \nUser Balance:{user_bal}")
                return
            if bid>200:
                    await ctx.send(f"{ctx.author.mention} bid is limited to 200! continuing lottery with 200 coins")
                    bid = 200
            choices = (['win','lose'] + ['win'] * 2 +['lose']*3+ ['win'] +['lose']*2+ ['win'] * 1+['lose']*3+ ['win'] * 2 +['lose']*4+ ['win'] * 3 +['lose']*3+ ['win'] * 2 +['lose']*3)
            choose = random.choice(choices)
            if choose == "win":
                choices = [2,3,4,2,2,4,2,3,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,2,2,2,2,2,2,2,2,2,2,2,2,2,2]
                times = random.choice(choices)
                win_amount = bid*times
                glob_fns().update_balance(ctx.author.id,win_amount,ctx.guild.id,False)
                outcome = f"{ctx.author.display_name} scratched a lottery and just won {win_amount} hill coins!"
            else:
                glob_fns().update_balance(ctx.author.id,bid,ctx.guild.id,True)
                outcome = f"{ctx.author.mention} scratched a lottery and won nothing \n:( ....."
            embed = discord.Embed(title="𓂀 𝐿𝑜𝓉𝓉𝑒𝓇𝓎 𝑅𝑒𝓈𝓊𝓁𝓉 𓂀", color=discord.Color.gold())
            embed.add_field(name=outcome,value="",inline=False)
            embed.set_image(url="https://t4.ftcdn.net/jpg/09/84/11/55/360_F_984115599_TpM2zxJjUIOsgK1V0Kca5EIcqs1MG6ar.jpg")
            embed.set_footer(text="Note: Greater the amount, greater the risk!")
            await ctx.send(f"{ctx.author.mention}", embed=embed)
        except Exception as e:
            print(f"❌ Error in lottery command: {type(e).__name__}: {e}")
            await ctx.send(f"An error occurred while processing your lottery: {e}")
    @lottery.error
    async def lottery_error(self,ctx:commands.Command,error):
        if isinstance(error,commands.MissingRequiredArgument):
            await ctx.send(f"Please spend some amount on lottery! Example : `p!lottery 150` \nNote! : Greater the amount , greater the risk and greater the reward!")
    @commands.command(name="truthanddare",aliases=['tnd',"TnD","TND"])
    @decorators.is_user()
    async def tnd(self,ctx:commands.Context):
        guild_data = glob_fns().load_guild(ctx.guild.id)
        tnd_channel = guild_data['TND_channel']
        if len(tnd_channel)<1:
            await ctx.send("Please ask your server adminstration to set a tnd channel")
            return
        if ctx.channel.id not in tnd_channel:
            channels = ""
            for chann in tnd_channel:
                channels += f"<#{chann}> , "
            await ctx.send(f"Please run the TND in a specified channel! \nAllowed channels: \n{channels}")
            return
        embed = discord.Embed(
        title="Truth or Dare",
        description="Click a button below to play!",
        color=discord.Color.gold()
        )
        view = TruthDareView()
        await ctx.send(embed=embed, view=view)
async def setup(bot:commands.Bot):
    await bot.add_cog(games(bot))