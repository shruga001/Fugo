import asyncio
from fns import *
import discord
from discord.ext import commands
import random
# new starts here
class RPSChoiceView(discord.ui.View):
    def __init__(self, game, player):
        super().__init__(timeout=30)
        self.game = game
        self.player = player

    @discord.ui.button(label="🪨 Rock", style=discord.ButtonStyle.primary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        await interaction.response.send_message("Choice recorded: Rock", ephemeral=True)
        self.disable_all_items()
        await interaction.message.edit(view=self)
        await self.game.record_choice(interaction.user, "rock")
    @discord.ui.button(label="📄 Paper", style=discord.ButtonStyle.success)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        await interaction.response.send_message("Choice recorded: Paper", ephemeral=True)
        self.disable_all_items()
        await interaction.message.edit(view=self)
        await self.game.record_choice(interaction.user, "paper")

    @discord.ui.button(label="✂️ Scissors", style=discord.ButtonStyle.danger)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        await interaction.response.send_message("Choice recorded: Scissors", ephemeral=True)
        self.disable_all_items()
        await interaction.message.edit(view=self)
        await self.game.record_choice(interaction.user, "scissors")

    def disable_all_items(self):
        for item in self.children:
            item.disabled = True

class RPSBotChoiceView(RPSChoiceView):
    def __init__(self, game):
        super().__init__(game, game.author)
class RPSChallengeBot():
    def __init__(self,author:discord.User,guild_id:int,ctx:commands.Context,bet:int):
        self.ctx = ctx
        self.author = author
        self.guild_id = guild_id
        self.finished = False
        self.bet = bet
    async def send_prompt(self):
        view = RPSBotChoiceView(self)
        self.message = await self.ctx.send(f"{self.ctx.author.mention} choose your move against bot!", view=view)
        await asyncio.sleep(30)
        if not self.finished:
            await self.ctx.send(f"{self.author.mention} you ran out of time!")
            view.disable_all_items()
            await self.message.edit(view=view)
    async def record_choice(self,user,choice):
        lose_to = {"rock":"paper","paper":"scissors","scissors":"rock"}
        win_against = {v:k for k,v in lose_to.items()}
        bot_outcomes = (
            [win_against[choice]] * 4 + 
            [choice] * 2 + 
            [lose_to[choice]] * 4
        )
        bot_choice = random.choice(bot_outcomes)
        result = RPSChallenge.determine_winner_static(choice,bot_choice)
        if result == "author":
            glob_fns().update_balance(self.author.id,self.bet,self.guild_id,False)
            outcome = f"{self.author.mention} wins! (Bot chose {bot_choice})"
        elif result == "opponent":
            glob_fns().update_balance(self.author.id,self.bet,self.guild_id,True)
            outcome = f"Bot wins! (Bot chose {bot_choice})"
        else:
            outcome = f"It's a draw! (Bot chose {bot_choice})"
        embed = discord.Embed(title="Rock Paper Scissors vs Bot", color=discord.Color.blurple())
        embed.add_field(name=self.author.display_name, value=choice, inline=True)
        embed.add_field(name="Bot", value=bot_choice, inline=True)
        embed.add_field(name="Outcome", value=outcome, inline=False)
        await self.ctx.send(embed=embed)
        self.finished = True
class RPSChallenge:
    def __init__(self,ctx:commands.Context,author:discord.Member,opponent:discord.Member,bet:int,guild_id:int):
        self.ctx = ctx
        self.author = author
        self.opponent = opponent
        self.bet = bet
        self.guild_id = guild_id
        self.choices = {}
    async def send_choices(self):
        self.view1 = RPSChoiceView(self,self.author)
        self.view2 = RPSChoiceView(self,self.opponent)
        self.message1 = await self.ctx.send(f"{self.author.mention}, make your move:", view=self.view1)
        self.message2 = await self.ctx.send(f"{self.opponent.mention}, make your move:", view=self.view2)
        await asyncio.sleep(30)
        if len(self.choices)<2:
            await self.ctx.send(f"Game between {self.author.mention} & {self.opponent.mention} timed out!")
            self.view1.disable_all_items()
            self.view2.disable_all_items()
            await self.message1.edit(view = self.view1)
            await self.message2.edit(view = self.view2)
    async def record_choice(self,user:discord.Member,choice):
        self.choices[user.id] = choice
        if len(self.choices)==2:
            await self.finish_game()
    async def finish_game(self):
        author_choice = self.choices[self.author.id]
        opponent_choice = self.choices[self.opponent.id]
        result = self.determine_winner(author_choice,opponent_choice)
        if result=="author":
            glob_fns().update_balance(self.author.id,self.bet,self.guild_id,False)
            glob_fns().update_balance(self.opponent.id,self.bet,self.guild_id,True)
            outcome = f"{self.author.mention} wins! the game between {self.author.mention} & {self.opponent.mention}"
        elif result=="opponent":
            glob_fns().update_balance(self.author.id,self.bet,self.guild_id,True)
            glob_fns().update_balance(self.opponent.id,self.bet,self.guild_id,False)
            outcome = f"{self.opponent.mention} wins! the game between {self.author.mention} & {self.opponent.mention}"
        else:
            outcome = f"The game between {self.author.mention} & {self.opponent.mention} reached a draw!"
        embed = discord.Embed(title="Rock Paper Scissors Result", color=discord.Color.blurple())
        embed.add_field(name=self.author.display_name, value=author_choice, inline=True)
        embed.add_field(name=self.opponent.display_name, value=opponent_choice, inline=True)
        embed.add_field(name="Outcome", value=outcome, inline=False)
        await self.ctx.send(embed=embed)
    def determine_winner(self, user1, user2):
        return RPSChallenge.determine_winner_static(user1, user2)
    @staticmethod
    def determine_winner_static(user1, user2):
        beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
        if user1 == user2:
            return "draw"
        elif beats[user1] == user2:
            return "author"
        else:
            return "opponent"