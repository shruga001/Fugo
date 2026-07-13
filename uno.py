import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import asyncio
import random
import json


# ─── Constants ───────────────────────────────────────────────────────────────

COLORS = {"red": "🔴", "green": "🟢", "blue": "🔵", "yellow": "🟡"}
ACTION_DISPLAY = {"skip": "Skip", "reverse": "Reverse", "draw_two": "+2"}
BOT_NAMES = ["Bot Alpha", "Bot Beta", "Bot Gamma"]
TURN_TIMEOUT = 30
MAX_PENALTIES = 3


def parse_card(card: str):
    """Return (color, value) tuple.  'draw_four' → (None, 'draw_four')."""
    if card == "draw_four":
        return None, "draw_four"
    color, value = card.split("_", 1)
    return color, value


def card_display(card: str) -> str:
    """Human-friendly card name."""
    if card == "draw_four":
        return "🌈 +4 Wild"
    color, value = parse_card(card)
    emoji = COLORS.get(color, "⬜")
    label = ACTION_DISPLAY.get(value, value)
    return f"{emoji} {label}"


def is_playable(card: str, top_card: str, current_color: str | None = None) -> bool:
    """Check whether *card* can be played on *top_card*."""
    if card == "draw_four":
        return True
    c_col, c_val = parse_card(card)
    t_col, t_val = parse_card(top_card)

    if c_col == t_col:
        return True
    if c_val == t_val:
        return True
    # Top is a wild – compare against the chosen colour
    if t_val == "draw_four" and current_color and c_col == current_color:
        return True
    return False


def get_next_turn_name(game) -> str:
    """Return the display name of the player whose turn is next."""
    direction = game["direction"]
    total = len(game["players"])
    if total == 0:
        return "nobody"
    next_idx = (game["turn_index"] + direction) % total
    next_p = game["players"][next_idx]
    if isinstance(next_p, str):
        return BOT_NAMES[int(next_p.split("_")[1])] if next_p.startswith("bot_") else next_p
    return next_p.mention


# ─── Main Cog ────────────────────────────────────────────────────────────────

class UnoGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games: dict[int, dict] = {}  # channel_id → game state
        print("UNO cog loaded.")

    # ── Commands ──────────────────────────────────────────────────────────

    @commands.command(name="uno")
    async def uno(self, ctx: commands.Context):
        """Start a new UNO game."""
        if ctx.channel.id in self.games:
            return await ctx.send("A game is already running in this channel.")

        # ── 1. Join phase ──────────────────────────────────────────────
        initiator = ctx.author
        msg = await ctx.send(
            f"{initiator.mention} wants to play **UNO**!\n"
            "React with ✅ within 30 seconds to join!"
        )
        await msg.add_reaction("✅")

        await asyncio.sleep(30)

        # Fetch the message fresh to get up-to-date reactions
        try:
            msg = await ctx.channel.fetch_message(msg.id)
        except discord.NotFound:
            return await ctx.send("Join message was deleted. Cancelling game.")

        reactors = set()
        for reaction in msg.reactions:
            if str(reaction.emoji) == "✅":
                async for user in reaction.users():
                    if not user.bot and user != initiator:
                        reactors.add(user)

        human_players = [initiator] + list(reactors)
        all_players = list(human_players)  # will mutate later

        # Determine bot count
        if len(human_players) == 1:
            needed = 3
        elif len(human_players) == 2:
            needed = 2
        elif len(human_players) == 3:
            needed = 1
        else:
            needed = 0

        bot_ids = []
        for i in range(needed):
            bid = f"bot_{i}"
            bot_ids.append(bid)
            all_players.append(bid)

        # ── 2. Deal ────────────────────────────────────────────────────
        with open("uno/deck.json") as f:
            deck = json.load(f)
        random.shuffle(deck)

        hands: dict = {}
        for p in all_players:
            pid = p.id if not isinstance(p, str) else p
            hands[pid] = [deck.pop() for _ in range(7)]

        top_card = deck.pop()
        # Re-shuffle if top card is a wild
        while top_card == "draw_four":
            deck.append(top_card)
            random.shuffle(deck)
            top_card = deck.pop()

        pile = [top_card]
        current_color, _ = parse_card(top_card)

        game: dict = {
            "players": all_players,           # list of discord.Member | str
            "hands": hands,
            "deck": deck,
            "pile": pile,
            "turn_index": 0,
            "direction": 1,                   # 1 = forward, -1 = reverse
            "current_color": current_color,
            "penalties": {p.id if not isinstance(p, str) else p: 0 for p in all_players},
            "uno_called": set(),
            "human_ids": {p.id for p in human_players},
            "channel_id": ctx.channel.id,
        }
        self.games[ctx.channel.id] = game

        names = []
        for p in all_players:
            if isinstance(p, str):
                names.append(BOT_NAMES[int(p.split("_")[1])] if p.startswith("bot_") else p)
            else:
                names.append(p.mention)
        await ctx.send(
            f"**UNO game starting!** Players: {', '.join(names)}\n"
            f"First card: **{card_display(top_card)}**\n"
            f"Use `ft!call` before playing your second-last card!"
        )

        # ── 3. Start the game loop ─────────────────────────────────────
        await self.game_loop(ctx, game)

    @commands.command(name="call")
    async def call_uno(self, ctx: commands.Context):
        """Call UNO when you have 2 cards left."""
        game = self.games.get(ctx.channel.id)
        if not game:
            return await ctx.send("No active UNO game in this channel.")
        if ctx.author.id not in game["human_ids"]:
            return await ctx.send("You are not a player in this game.")

        hand = game["hands"].get(ctx.author.id, [])
        if len(hand) == 2:
            game["uno_called"].add(ctx.author.id)
            await ctx.send(f"{ctx.author.mention} called **UNO!**")
        else:
            # Penalty for false call
            if game["deck"]:
                drawn = game["deck"].pop()
                game["hands"][ctx.author.id].append(drawn)
                await ctx.send(
                    f"{ctx.author.mention} invalid UNO call! Drew **{card_display(drawn)}** as penalty."
                )
            else:
                await ctx.send("Invalid UNO call!")

    # ── Game Loop ───────────────────────────────────────────────────────

    async def game_loop(self, ctx: commands.Context, game: dict):
        """Advance through turns until someone wins or all are eliminated."""
        while ctx.channel.id in self.games:
            game = self.games[ctx.channel.id]
            players = game["players"]
            if not players:
                await ctx.send("All players have been eliminated! No winner.")
                del self.games[ctx.channel.id]
                return

            idx = game["turn_index"]
            if idx >= len(players):
                game["turn_index"] = 0
                idx = 0

            current = players[idx]
            pid = current.id if not isinstance(current, str) else current

            # ── Bot turn ────────────────────────────────────────────
            if isinstance(current, str) or pid not in game["human_ids"]:
                await self.bot_turn(ctx, game, current, pid)
            else:
                await self.human_turn(ctx, game, current)

            # After the turn, check for winner
            game = self.games.get(ctx.channel.id)
            if not game:
                return  # game was already deleted (someone won)

            pid_after = current.id if not isinstance(current, str) else current
            if not game["hands"].get(pid_after):
                # Winner! game already cleaned up in human_turn/bot_turn
                return

            # Check if all players are eliminated
            if not game["players"]:
                await ctx.send("All players have been eliminated! No winner.")
                del self.games[ctx.channel.id]
                return

            # Advance turn
            direction = game["direction"]
            total = len(game["players"])
            game["turn_index"] = (game["turn_index"] + direction) % total

            # Announce next turn
            next_name = get_next_turn_name(game)
            await ctx.send(f"➡️ Next up: {next_name}")

            await asyncio.sleep(1.5)  # brief pause between turns

    # ── Bot AI ───────────────────────────────────────────────────────────

    async def bot_turn(self, ctx, game, bot_id, pid):
        """Handle a bot player's turn."""
        await asyncio.sleep(random.uniform(1.0, 2.5))  # "thinking" delay

        name = BOT_NAMES[int(pid.split("_")[1])] if pid.startswith("bot_") else pid

        hand = game["hands"][pid]
        top = game["pile"][-1]
        usable = [c for c in hand if is_playable(c, top, game["current_color"])]

        if not usable:
            # Draw a card
            if game["deck"]:
                drawn = game["deck"].pop()
                hand.append(drawn)
                await ctx.send(f"**{name}** draws a card.")
                # Check if the drawn card is playable
                if is_playable(drawn, top, game["current_color"]):
                    usable = [drawn]
                else:
                    await ctx.send(f"**{name}** has no playable cards. Turn skipped.")
                    return
            else:
                await ctx.send(f"**{name}** has no playable cards. Turn skipped.")
                return

        # Choose a card to play
        chosen = self.bot_choose_card(usable, hand)
        hand.remove(chosen)

        # Auto-call UNO if going to 1 card
        if len(hand) == 1:
            game["uno_called"].add(pid)

        await ctx.send(f"**{name}** played **{card_display(chosen)}**")

        # Apply action effects
        await self.apply_card_effects(ctx, game, chosen, pid, name)

        # Handle deck recycling
        await self.maybe_recycle_deck(game)

        # Check win
        if not hand:
            await ctx.send(f"🏁 **{name}** has won the game!")
            del self.games[ctx.channel.id]
            return

    def bot_choose_card(self, playable, hand):
        """Simple AI: prefer action cards, avoid wilds if possible."""
        non_wild = [c for c in playable if c != "draw_four"]
        if non_wild:
            actions = [c for c in non_wild if parse_card(c)[1] in ("skip", "reverse", "draw_two")]
            if actions:
                return random.choice(actions)
            return random.choice(non_wild)
        return random.choice(playable)

    # ── Human Turn ──────────────────────────────────────────────────────

    async def human_turn(self, ctx, game, player):
        """Present a view to the human player for their turn."""
        pid = player.id
        hand = game["hands"][pid]
        top = game["pile"][-1]
        playable = [c for c in hand if is_playable(c, top, game["current_color"])]

        # Send public announcement
        msg = await ctx.send(f"⏳ {player.mention}'s turn!")

        # Ephemeral hand via DM
        view = TurnView(self, ctx, game, player, playable)
        hand_text = "\n".join(f"{i+1}. {card_display(c)}" for i, c in enumerate(hand))
        embed = discord.Embed(
            title="Your Hand",
            description=f"Top card: **{card_display(top)}**\n\n{hand_text}",
            color=discord.Color.blue(),
        )

        # Add a note if no playable cards (auto-draw will happen)
        if not playable:
            embed.set_footer(text="No playable cards — drawing automatically!")
            await ctx.send(f"🃏 {player.mention} has no playable cards. Drawing automatically...")
            # Auto-draw
            if game["deck"]:
                drawn = game["deck"].pop()
                hand.append(drawn)
                await ctx.send(f"{player.mention} drew **{card_display(drawn)}**")
                # Check if drawn card is playable
                if is_playable(drawn, top, game["current_color"]):
                    playable = [drawn]
                await self.maybe_recycle_deck(game)
            # If still no playable, turn is skipped
            if not playable:
                await ctx.send(f"{player.mention} still has no playable cards. Turn skipped.")
                # Still need to give the view so they can see their hand, but mark finished
                view.finished = True
                try:
                    await player.send(embed=embed, view=view)
                except discord.Forbidden:
                    private_channel = await self._create_private_channel(ctx, player)
                    await private_channel.send(embed=embed, view=view)
                    await self._delete_channel_later(private_channel)
                return

        private_channel = None
        try:
            await player.send(embed=embed, view=view)
        except discord.Forbidden:
            # DM failed — create a private channel in the same category
            private_channel = await self._create_private_channel(ctx, player)
            await private_channel.send(
                f"{player.mention} here is your hand for the current turn!",
                embed=embed,
                view=view,
            )

        # Wait for the view to complete or timeout
        await view.wait()

        # Delete private channel if it was created
        if private_channel:
            await self._delete_channel_later(private_channel)

        # If the game was deleted, player won
        if ctx.channel.id not in self.games:
            return

        game = self.games[ctx.channel.id]
        hand = game["hands"].get(pid, [])

        # Check win after playing
        if not hand:
            await ctx.send(f"🏁 {player.mention} has won the game!")
            del self.games[ctx.channel.id]
            return

    async def _create_private_channel(self, ctx, player):
        """Create a temporary private text channel for a player's UNO hand."""
        category = ctx.channel.category
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            player: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        return await ctx.guild.create_text_channel(
            f"uno-{player.name}",
            category=category,
            overwrites=overwrites,
            reason=f"Private UNO hand channel for {player.name}",
        )

    async def _delete_channel_later(self, channel):
        """Delete a private channel with a short delay."""
        try:
            await asyncio.sleep(1)
            await channel.delete(reason="UNO turn completed")
        except (discord.Forbidden, discord.NotFound):
            pass

    # ── Apply Card Effects ──────────────────────────────────────────────

    async def apply_card_effects(self, ctx, game, played_card, player_id, name=None):
        """Apply action-card effects (skip, reverse, draw_two, draw_four)."""
        _, val = parse_card(played_card)

        if val == "skip":
            game["turn_index"] = (game["turn_index"] + game["direction"]) % len(game["players"])
            await ctx.send(f"⏭️ Next player is skipped!")

        elif val == "reverse":
            game["direction"] *= -1
            await ctx.send(f"🔄 Direction reversed!")
            if len(game["players"]) == 2:
                game["turn_index"] = (game["turn_index"] + game["direction"]) % len(game["players"])
                await ctx.send(f"⏭️ Next player is skipped!")

        elif val == "draw_two":
            next_idx = (game["turn_index"] + game["direction"]) % len(game["players"])
            next_p = game["players"][next_idx]
            next_pid = next_p.id if not isinstance(next_p, str) else next_p
            drawn = []
            for _ in range(2):
                if game["deck"]:
                    drawn.append(game["deck"].pop())
            game["hands"][next_pid].extend(drawn)
            drawn_text = ", ".join(card_display(c) for c in drawn) if drawn else "nothing"
            next_name = name if next_pid == player_id else (
                next_p.mention if not isinstance(next_p, str)
                else BOT_NAMES[int(next_pid.split("_")[1])]
            )
            await ctx.send(f"⏭️ {next_name} draws 2 and is skipped! ({drawn_text})")
            game["turn_index"] = (game["turn_index"] + game["direction"]) % len(game["players"])

        elif val == "draw_four":
            next_idx = (game["turn_index"] + game["direction"]) % len(game["players"])
            next_p = game["players"][next_idx]
            next_pid = next_p.id if not isinstance(next_p, str) else next_p
            drawn = []
            for _ in range(4):
                if game["deck"]:
                    drawn.append(game["deck"].pop())
            game["hands"][next_pid].extend(drawn)
            drawn_text = ", ".join(card_display(c) for c in drawn) if drawn else "nothing"
            next_name = next_p.mention if not isinstance(next_p, str) else (
                BOT_NAMES[int(next_pid.split("_")[1])]
            )
            await ctx.send(f"⏭️ {next_name} draws 4 and is skipped! ({drawn_text})")
            game["turn_index"] = (game["turn_index"] + game["direction"]) % len(game["players"])

    # ── Helpers ─────────────────────────────────────────────────────────

    async def maybe_recycle_deck(self, game):
        """When the draw pile runs out, recycle the discard pile."""
        if not game["deck"] and len(game["pile"]) > 1:
            top = game["pile"][-1]
            game["deck"] = game["pile"][:-1]
            game["pile"] = [top]
            random.shuffle(game["deck"])

    def remove_player(self, ctx, game, player_id):
        """Remove a player from the game (penalties maxed out)."""
        # Add their cards back to the deck
        if player_id in game["hands"]:
            game["deck"].extend(game["hands"][player_id])
            random.shuffle(game["deck"])
        # Find and remove from players list
        for i, p in enumerate(game["players"]):
            pid = p.id if not isinstance(p, str) else p
            if pid == player_id:
                game["players"].pop(i)
                break
        # Clean up their hand
        game["hands"].pop(player_id, None)
        game["penalties"].pop(player_id, None)
        game["uno_called"].discard(player_id)

        # Adjust turn index if needed
        total = len(game["players"])
        if total == 0:
            return
        if game["turn_index"] >= total:
            game["turn_index"] = 0


# ─── UI Views ────────────────────────────────────────────────────────────────

class TurnView(View):
    """View shown to a human player on their turn. Timeout = 30 s."""

    def __init__(self, cog, ctx, game, player, playable_cards):
        super().__init__(timeout=TURN_TIMEOUT)
        self.cog = cog
        self.ctx = ctx
        self.game = game
        self.player = player
        self.pid = player.id
        self.playable = playable_cards
        self.finished = False

        # Card dropdown (only shown if there are playable cards)
        if playable_cards:
            options = [
                discord.SelectOption(label=card_display(c), value=c)
                for c in playable_cards
            ]
            self.select = Select(placeholder="Choose a card to play…", options=options)
            self.select.callback = self.card_selected
            self.add_item(self.select)

        # Draw button
        draw_btn = Button(label="Draw Card", style=discord.ButtonStyle.secondary, row=1)
        draw_btn.callback = self.draw_clicked
        self.add_item(draw_btn)

        # UNO call button
        uno_btn = Button(label="Call UNO!", style=discord.ButtonStyle.danger, row=1)
        uno_btn.callback = self.uno_clicked
        self.add_item(uno_btn)

    async def card_selected(self, interaction: discord.Interaction):
        if interaction.user.id != self.pid:
            return await interaction.response.send_message("Not your turn!", ephemeral=True)

        chosen = self.select.values[0]

        # ── Validate the card is actually in the player's hand ────────
        hand = self.game["hands"][self.pid]
        if chosen not in hand:
            return await interaction.response.send_message(
                "You no longer have that card!", ephemeral=True
            )

        # ── Validate the card is actually playable ────────────────────
        top = self.game["pile"][-1]
        color = self.game["current_color"]
        if not is_playable(chosen, top, color):
            return await interaction.response.send_message(
                f"**{card_display(chosen)}** cannot be played on **{card_display(top)}**! "
                "Choose a valid card or draw.",
                ephemeral=True,
            )

        # ── UNO check ────────────────────────────────────────────
        if len(hand) == 2:  # about to go to 1
            if self.pid not in self.game["uno_called"]:
                # Penalty: draw 4 cards
                drawn = []
                for _ in range(4):
                    if self.game["deck"]:
                        drawn.append(self.game["deck"].pop())
                hand.extend(drawn)
                drawn_text = ", ".join(card_display(c) for c in drawn) if drawn else "nothing"
                await interaction.response.send_message(
                    f"You forgot to call UNO! Draw 4 penalty cards: {drawn_text}",
                    ephemeral=True,
                )
                await self.ctx.send(f"{self.player.mention} forgot to call UNO and drew 4 penalty cards!")
                self.finished = True
                self.stop()
                await self.cog.maybe_recycle_deck(self.game)
                return
            else:
                self.game["uno_called"].discard(self.pid)

        # ── Play the card ────────────────────────────────────────
        hand.remove(chosen)
        self.game["pile"].append(chosen)

        await interaction.response.send_message(
            f"You played **{card_display(chosen)}**", ephemeral=True
        )
        await self.ctx.send(f"{self.player.mention} played **{card_display(chosen)}**")

        # ── Wild colour picker ───────────────────────────────────
        if chosen == "draw_four":
            await self.ctx.send("Choose a colour:", view=WildColorView(self.cog, self.ctx, self.game, self.pid))
        else:
            # Update current colour
            col, _ = parse_card(chosen)
            self.game["current_color"] = col
            # Apply effects
            await self.cog.apply_card_effects(self.ctx, self.game, chosen, self.pid)
            await self.cog.maybe_recycle_deck(self.game)

        self.finished = True
        self.stop()

    async def draw_clicked(self, interaction: discord.Interaction):
        if interaction.user.id != self.pid:
            return await interaction.response.send_message("Not your turn!", ephemeral=True)

        if self.game["deck"]:
            drawn = self.game["deck"].pop()
            self.game["hands"][self.pid].append(drawn)
            await interaction.response.send_message(
                f"You drew **{card_display(drawn)}**", ephemeral=True
            )
        else:
            await interaction.response.send_message("Deck is empty! Turn skipped.", ephemeral=True)

        await self.cog.maybe_recycle_deck(self.game)
        await self.ctx.send(f"{self.player.mention} drew a card and passed.")
        self.finished = True
        self.stop()

    async def uno_clicked(self, interaction: discord.Interaction):
        if interaction.user.id != self.pid:
            return await interaction.response.send_message("Not your turn!", ephemeral=True)

        hand = self.game["hands"][self.pid]
        if len(hand) == 2:
            self.game["uno_called"].add(self.pid)
            await interaction.response.send_message("**UNO!** call registered!", ephemeral=True)
        else:
            # Penalty for false call
            if self.game["deck"]:
                drawn = self.game["deck"].pop()
                self.game["hands"][self.pid].append(drawn)
                await interaction.response.send_message(
                    f"Invalid UNO call! Drew **{card_display(drawn)}** as penalty.", ephemeral=True
                )
            else:
                await interaction.response.send_message("Invalid UNO call!", ephemeral=True)

        await self.cog.maybe_recycle_deck(self.game)

    async def on_timeout(self):
        """Player didn't interact in time – auto-draw + skip."""
        if self.finished:
            return
        if self.ctx.channel.id not in self.cog.games:
            return

        game = self.cog.games[self.ctx.channel.id]
        if self.pid not in game["hands"]:
            return

        hand = game["hands"][self.pid]
        # Auto-draw
        if game["deck"]:
            drawn = game["deck"].pop()
            hand.append(drawn)
            await self.ctx.send(f"⏰ {self.player.mention} timed out! Drew **{card_display(drawn)}** and turn skipped.")
        else:
            await self.ctx.send(f"⏰ {self.player.mention} timed out! No cards left in deck, turn skipped.")

        # Increment penalty counter
        game["penalties"][self.pid] = game["penalties"].get(self.pid, 0) + 1
        await self.ctx.send(
            f"⚠️ {self.player.mention} penalty {game['penalties'][self.pid]}/{MAX_PENALTIES}"
        )

        # Check if player should be removed
        if game["penalties"][self.pid] >= MAX_PENALTIES:
            await self.ctx.send(f"💀 {self.player.mention} has been eliminated from the game!")
            self.cog.remove_player(self.ctx, game, self.pid)

        await self.cog.maybe_recycle_deck(game)
        self.finished = True


class WildColorView(View):
    """Choose a colour after playing a wild card."""

    def __init__(self, cog, ctx, game, player_id):
        super().__init__(timeout=15)
        self.cog = cog
        self.ctx = ctx
        self.game = game
        self.pid = player_id
        self.value = None

    @discord.ui.button(label="Red", style=discord.ButtonStyle.danger, emoji="🔴", row=0)
    async def red_btn(self, interaction: discord.Interaction, btn):
        await self.pick_color(interaction, "red")

    @discord.ui.button(label="Green", style=discord.ButtonStyle.success, emoji="🟢", row=0)
    async def green_btn(self, interaction: discord.Interaction, btn):
        await self.pick_color(interaction, "green")

    @discord.ui.button(label="Blue", style=discord.ButtonStyle.primary, emoji="🔵", row=1)
    async def blue_btn(self, interaction: discord.Interaction, btn):
        await self.pick_color(interaction, "blue")

    @discord.ui.button(label="Yellow", style=discord.ButtonStyle.secondary, emoji="🟡", row=1)
    async def yellow_btn(self, interaction: discord.Interaction, btn):
        await self.pick_color(interaction, "yellow")

    async def pick_color(self, interaction: discord.Interaction, color: str):
        if interaction.user.id != self.pid:
            return await interaction.response.send_message("Not your turn!", ephemeral=True)

        self.game["current_color"] = color
        await interaction.response.edit_message(
            content=f"Colour changed to **{COLORS[color]} {color.capitalize()}**",
            view=None,
        )

        # Find the last played card (the wild) and apply effects
        last_card = self.game["pile"][-1]
        await self.cog.apply_card_effects(self.ctx, self.game, last_card, self.pid)
        await self.cog.maybe_recycle_deck(self.game)
        self.stop()

    async def on_timeout(self):
        self.stop()


# ─── Setup ───────────────────────────────────────────────────────────────────

async def setup(bot):
    await bot.add_cog(UnoGame(bot))