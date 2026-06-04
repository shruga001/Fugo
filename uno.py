import discord
from discord.ext import commands
import asyncio
import random
import json

class UnoGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # {channel_id: game_data}
        print("UNO cog loaded.")

    @commands.command()
    async def uno(self, ctx):
        await ctx.send("UNO is temporary unavailable while we work on improvements. Please check back later!")
        return
        """Starts a new UNO game."""
        if ctx.channel.id in self.games:
            return await ctx.send("A game is already running in this channel.")

        join_message = await ctx.send("React with ✅ to join UNO! Game starts in 30 seconds...")
        await join_message.add_reaction("✅")
        initiator = ctx.author

        await asyncio.sleep(30)
        join_message = await ctx.channel.fetch_message(join_message.id)
        users = set()

        for reaction in join_message.reactions:
            if str(reaction.emoji) == "✅":
                async for user in reaction.users():
                    if not user.bot:
                        users.add(user)

        users.add(initiator)
        players = list(users)

        if len(players) < 3:
            return await ctx.send("Not enough players. Minimum 3 required to start UNO.")

        await ctx.send(f"Starting UNO with: {', '.join([p.mention for p in players])}")

        with open("uno/deck.json") as f:
            deck = json.load(f)
        with open("uno/uno.json") as f:
            rules = json.load(f)

        random.shuffle(deck)
        hands = {p.id: [deck.pop() for _ in range(7)] for p in players}
        top_card = deck.pop()

        self.games[ctx.channel.id] = {
            "players": players,
            "hands": hands,
            "deck": deck,
            "pile": [top_card],
            "turn": 0,
            "rules": rules,
            "uno_flags": set()
        }

        await ctx.send(f"UNO is starting! First card: **{top_card}**")
        await self.prompt_turn(ctx)

    async def prompt_turn(self, ctx):
        game = self.games[ctx.channel.id]
        current_player = game["players"][game["turn"]]

        embed = discord.Embed(
            title="UNO Turn",
            description=f"It's {current_player.mention}'s turn!",
            color=discord.Color.blue()
        )
        view = TurnButtonView(ctx, current_player, self)
        await ctx.send(embed=embed, view=view)

    async def next_turn(self, ctx):
        game = self.games[ctx.channel.id]
        game["turn"] = (game["turn"] + 1) % len(game["players"])
        await self.prompt_turn(ctx)

    async def send_turn_dropdown(self, interaction, ctx, player):
        game = self.games[ctx.channel.id]
        hand = game["hands"][player.id]
        top_card = game["pile"][-1]
        playable = [
            card for card in hand
            if card in game["rules"][top_card]["top"] or card in ["wild", "draw_four"]
        ]

        if not playable:
            drawn = game["deck"].pop()
            game["hands"][player.id].append(drawn)
            await interaction.response.send_message(f"No playable cards! Drew: `{drawn}`", ephemeral=True)
            await self.next_turn(ctx)
            return

        view = PlayCardView(self, ctx, player, playable)
        await interaction.response.send_message("Your hand:", view=view, ephemeral=True)


class TurnButtonView(discord.ui.View):
    def __init__(self, ctx, current_player, cog):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.current_player = current_player
        self.cog = cog

    @discord.ui.button(label="Take Turn", style=discord.ButtonStyle.primary)
    async def take_turn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player.id:
            await interaction.response.send_message(
                f"It's {self.current_player.mention}'s turn.", ephemeral=True
            )
        else:
            await self.cog.send_turn_dropdown(interaction, self.ctx, self.current_player)
            self.stop()


class PlayCardView(discord.ui.View):
    def __init__(self, cog, ctx, player, cards):
        super().__init__(timeout=60)
        self.add_item(CardDropdown(cards, cog, ctx, player))
        self.add_item(UnoButton(cog, ctx, player))


class CardDropdown(discord.ui.Select):
    def __init__(self, cards, cog, ctx, player):
        options = [discord.SelectOption(label=card, value=card) for card in cards]
        super().__init__(placeholder="Choose a card to play", options=options)
        self.cog = cog
        self.ctx = ctx
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        game = self.cog.games[self.ctx.channel.id]
        chosen = self.values[0]
        game["hands"][self.player.id].remove(chosen)
        game["pile"].append(chosen)

        if len(game["hands"][self.player.id]) == 1:
            if self.player.id not in game["uno_flags"]:
                penalty = [game["deck"].pop() for _ in range(2)]
                game["hands"][self.player.id].extend(penalty)
                await interaction.followup.send(
                    "You forgot to call UNO! Drew 2 penalty cards.", ephemeral=True
                )
            else:
                game["uno_flags"].discard(self.player.id)

        await self.ctx.send(f"{self.player.mention} played **{chosen}**")

        if not game["hands"][self.player.id]:
            await self.ctx.send(f"🏁 {self.player.mention} has won the game!")
            del self.cog.games[self.ctx.channel.id]
            return
        if not game["deck"]:
            game["deck"] = game["pile"][:-1]
            game["pile"] = [game["pile"][-1]]
            random.shuffle(game["deck"])
            await self.ctx.send("Deck is empty! Shuffling the pile back into the deck.")
        await self.cog.next_turn(self.ctx)


class UnoButton(discord.ui.Button):
    def __init__(self, cog, ctx, player):
        super().__init__(label="UNO!", style=discord.ButtonStyle.danger)
        self.cog = cog
        self.ctx = ctx
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        game = self.cog.games[self.ctx.channel.id]
        if len(game["hands"][self.player.id]) != 2:
            drawn = game["deck"].pop()
            game["hands"][self.player.id].append(drawn)
            await interaction.response.send_message(
                "Invalid UNO call! Drew 1 penalty card.", ephemeral=True
            )
        else:
            game["uno_flags"].add(self.player.id)
            await interaction.response.send_message("UNO call registered!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(UnoGame(bot))
