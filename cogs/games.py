import asyncio
import random
from typing import Optional

import discord
from discord import ui as dui
from discord.ext import commands

import config
from core import ui
from core.base import MalfoyCog
from core.emojis import E
from core.utils import fmt, parse_amount

SUITS = ["\u2660\ufe0e", "\u2665\ufe0e", "\u2666\ufe0e", "\u2663\ufe0e"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
REDS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

SLOT_SYMBOLS = [
    ("SLOT_CHERRY", "Cherry", 30, 3),
    ("SLOT_LEMON", "Lemon", 25, 4),
    ("SLOT_BELL", "Bell", 18, 6),
    ("SLOT_CLOVER", "Clover", 12, 10),
    ("SLOT_GEM", "Gem", 10, 15),
    ("SLOT_SEVEN", "Seven", 5, 40),
]


def hand_value(cards):
    total = 0
    aces = 0
    for rank, _ in cards:
        if rank == "A":
            aces += 1
            total += 11
        elif rank in ("J", "Q", "K"):
            total += 10
        else:
            total += int(rank)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def show(cards, hide_second=False):
    shown = [f"{r}{s}" for r, s in cards]
    if hide_second and len(shown) > 1:
        shown[1] = "??"
    return " ".join(f"`{c}`" for c in shown)


def outcome_accent(outcome):
    return {"win": config.ACCENT_OK, "lose": config.ACCENT_ERR, "push": config.ACCENT_WARN}.get(outcome, config.ACCENT)


class BlackjackView(ui.Layout):
    def __init__(self, cog, ctx, bet):
        super().__init__(author=ctx.author, timeout=120)
        self.cog = cog
        self.bot = cog.bot
        self.ctx = ctx
        self.bet = bet
        self.deck = [(r, s) for r in RANKS for s in SUITS]
        random.shuffle(self.deck)
        self.player = [self.deck.pop(), self.deck.pop()]
        self.dealer = [self.deck.pop(), self.deck.pop()]
        self.done = False
        self.first_move = True

    def table(self, reveal, footer, accent=None):
        pv = hand_value(self.player)
        dv = hand_value(self.dealer) if reveal else hand_value(self.dealer[:1])
        rows = [
            ("You", f"{show(self.player)} ({pv})"),
            (config.BOT_NAME, f"{show(self.dealer, hide_second=not reveal)} ({dv if reveal else '?'})"),
        ]
        return [ui.head(E.CARDS, "Blackjack"), ui.sep(), ui.text(ui.bullets(rows)), ui.sep(), ui.text(footer)]

    def buttons(self):
        hit = dui.Button(style=discord.ButtonStyle.primary, label="Hit")
        stand = dui.Button(style=discord.ButtonStyle.secondary, label="Stand")
        double = dui.Button(style=discord.ButtonStyle.success, label="Double", disabled=not self.first_move)
        hit.callback = self.on_hit
        stand.callback = self.on_stand
        double.callback = self.on_double
        return ui.row(hit, stand, double)

    def render_live(self):
        self.clear_items()
        footer = f"- **Bet:** {fmt(self.bet)} {config.CURRENCY}\n- **Rule:** Dealer stands on 17"
        self.add_item(ui.card(*self.table(False, footer), ui.sep(), self.buttons()))

    def dealer_play(self):
        while hand_value(self.dealer) < 17:
            self.dealer.append(self.deck.pop())

    async def finish(self, outcome):
        self.done = True
        self.cog.bot.active_games.discard(self.ctx.author.id)
        payout = {"blackjack": int(self.bet * 2.5), "win": self.bet * 2, "push": self.bet}.get(outcome, 0)
        balance = await self.bot.db.settle(self.ctx.author.id, self.bet, payout)
        net = payout - self.bet
        labels = {
            "blackjack": f"{E.STAR} Blackjack! You won **{fmt(net)}** {config.CURRENCY}",
            "win": f"{E.TICK} You won **{fmt(net)}** {config.CURRENCY}",
            "push": f"{E.WARN} Push. Your bet was returned",
            "bust": f"{E.DENIED} Bust! You lost **{fmt(self.bet)}** {config.CURRENCY}",
            "lose": f"{E.DENIED} Dealer wins. You lost **{fmt(self.bet)}** {config.CURRENCY}",
        }
        kind = "win" if outcome in ("blackjack", "win") else "push" if outcome == "push" else "lose"
        self.clear_items()
        self.add_item(ui.card(*self.table(True, f"{labels[outcome]}\n- **Balance:** {fmt(balance)}"), accent=outcome_accent(kind)))
        self.stop()

    def settle_stand(self):
        self.dealer_play()
        pv, dv = hand_value(self.player), hand_value(self.dealer)
        if dv > 21 or pv > dv:
            return "win"
        if pv == dv:
            return "push"
        return "lose"

    async def on_hit(self, interaction):
        self.first_move = False
        self.player.append(self.deck.pop())
        value = hand_value(self.player)
        if value > 21:
            await self.finish("bust")
        elif value == 21:
            await self.finish(self.settle_stand())
        else:
            self.render_live()
        await interaction.response.edit_message(view=self)

    async def on_stand(self, interaction):
        await self.finish(self.settle_stand())
        await interaction.response.edit_message(view=self)

    async def on_double(self, interaction):
        if not await self.bot.db.take_cash(self.ctx.author.id, self.bet):
            return await interaction.response.send_message(
                view=ui.Notice("err", "You don't have enough cash to double down."), ephemeral=True
            )
        self.bet *= 2
        self.player.append(self.deck.pop())
        if hand_value(self.player) > 21:
            await self.finish("bust")
        else:
            await self.finish(self.settle_stand())
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        if self.done:
            return
        await self.finish(self.settle_stand())
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class RpsView(ui.Layout):
    CHOICES = ["Rock", "Paper", "Scissors"]
    BEATS = {"Rock": "Scissors", "Paper": "Rock", "Scissors": "Paper"}

    def __init__(self, cog, ctx, bet):
        super().__init__(author=ctx.author, timeout=45)
        self.cog = cog
        self.ctx = ctx
        self.bet = bet
        self.done = False
        buttons = []
        for name in self.CHOICES:
            button = dui.Button(style=discord.ButtonStyle.primary, label=name)
            button.callback = self.make_callback(name)
            buttons.append(button)
        self.add_item(
            ui.card(
                ui.head(E.GAMES, "Rock Paper Scissors"),
                ui.sep(),
                ui.text(f"Pick your move.\n- **Bet:** {fmt(bet)} {config.CURRENCY}"),
                ui.sep(),
                ui.row(*buttons),
            )
        )

    def make_callback(self, name):
        async def callback(interaction):
            await self.play(interaction, name)

        return callback

    async def play(self, interaction, mine):
        self.done = True
        theirs = random.choice(self.CHOICES)
        self.cog.bot.active_games.discard(self.ctx.author.id)
        if mine == theirs:
            outcome, payout = "push", self.bet
        elif self.BEATS[mine] == theirs:
            outcome, payout = "win", self.bet * 2
        else:
            outcome, payout = "lose", 0
        balance = await self.cog.bot.db.settle(self.ctx.author.id, self.bet, payout)
        line = {
            "win": f"{E.TICK} You won **{fmt(self.bet)}** {config.CURRENCY}",
            "lose": f"{E.DENIED} You lost **{fmt(self.bet)}** {config.CURRENCY}",
            "push": f"{E.WARN} A tie. Your bet was returned",
        }[outcome]
        self.clear_items()
        self.add_item(
            ui.card(
                ui.head(E.GAMES, "Rock Paper Scissors"),
                ui.sep(),
                ui.text(ui.bullets([("You", mine), (config.BOT_NAME, theirs)])),
                ui.sep(),
                ui.text(f"{line}\n- **Balance:** {fmt(balance)}"),
                accent=outcome_accent(outcome),
            )
        )
        self.stop()
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        if self.done:
            return
        self.cog.bot.active_games.discard(self.ctx.author.id)
        await self.cog.bot.db.settle(self.ctx.author.id, self.bet, self.bet)
        self.clear_items()
        self.add_item(ui.card(ui.text(f"{E.WARN} You took too long. Your bet was returned."), accent=config.ACCENT_WARN))
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Games(MalfoyCog):
    category = "Games"
    groups = [("Casino", ["coinflip", "slots", "blackjack", "roulette", "dice", "rps"])]

    async def read_bet(self, ctx, raw):
        row = await self.bot.db.user(ctx.author.id)
        try:
            return parse_amount(raw if raw is not None else str(config.DEFAULT_BET), row["cash"], maximum=config.MAX_BET)
        except commands.BadArgument as exc:
            await ui.notice(ctx, "err", str(exc))
            return None

    async def begin(self, ctx, raw):
        bet = await self.read_bet(ctx, raw)
        if bet is None:
            return None
        uid = ctx.author.id
        if uid in self.bot.active_games:
            await ui.notice(ctx, "warn", "Finish your current game first.")
            return None
        if not await self.bot.db.take_cash(uid, bet):
            await ui.notice(ctx, "err", "You don't have enough cash for that bet.")
            return None
        self.bot.active_games.add(uid)
        return bet

    def end(self, ctx):
        self.bot.active_games.discard(ctx.author.id)

    async def conclude(self, ctx, bet, payout, title, icon, lines, message=None):
        balance = await self.bot.db.settle(ctx.author.id, bet, payout)
        net = payout - bet
        if net > 0:
            verdict, kind = f"{E.TICK} You won **{fmt(net)}** {config.CURRENCY}", "win"
        elif net < 0:
            verdict, kind = f"{E.DENIED} You lost **{fmt(-net)}** {config.CURRENCY}", "lose"
        else:
            verdict, kind = f"{E.WARN} Your bet was returned", "push"
        view = ui.Static(
            ui.head(icon, title),
            ui.sep(),
            ui.text("\n".join(lines)),
            ui.sep(),
            ui.text(f"{verdict}\n- **Balance:** {fmt(balance)}"),
            accent=outcome_accent(kind),
        )
        if message is not None:
            await message.edit(view=view)
        else:
            await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="coinflip", aliases=["cf", "flip"], help="Flip a coin. Win double your bet.")
    async def coinflip(self, ctx, bet: Optional[str] = None, side: Optional[str] = None):
        sides = {"h": "Heads", "heads": "Heads", "t": "Tails", "tails": "Tails"}
        if bet and bet.lower() in sides:
            bet, side = side, bet
        choice = sides.get((side or "heads").lower())
        if choice is None:
            return await ui.notice(ctx, "err", "Choose `heads` or `tails`.")
        amount = await self.begin(ctx, bet)
        if amount is None:
            return
        try:
            wait = ui.Static(ui.head(E.SLOT_SPIN, "Coin Flip"), ui.sep(), ui.text("Flipping the coin..."))
            message = await ctx.reply(view=wait, mention_author=False)
            await asyncio.sleep(1.2)
            landed = random.choice(["Heads", "Tails"])
            payout = amount * 2 if landed == choice else 0
            lines = [f"- **You chose:** {choice}", f"- **Landed on:** {landed}"]
            await self.conclude(ctx, amount, payout, "Coin Flip", E.COIN, lines, message)
        finally:
            self.end(ctx)

    @commands.hybrid_command(name="slots", aliases=["slot", "spin"], help="Spin the slot machine.")
    async def slots(self, ctx, bet: Optional[str] = None):
        amount = await self.begin(ctx, bet)
        if amount is None:
            return
        try:
            keys = [s[0] for s in SLOT_SYMBOLS]
            weights = [s[2] for s in SLOT_SYMBOLS]
            reels = random.choices(keys, weights=weights, k=3)

            def sym(key):
                return E(key) or key.split("_")[1].title()

            spin = E.SLOT_SPIN or "[?]"

            def frame(revealed):
                cells = [sym(reels[i]) if i < revealed else spin for i in range(3)]
                return ui.Static(ui.head(E.SLOT_SEVEN, "Slots"), ui.sep(), ui.text("  ".join(cells)))

            message = await ctx.reply(view=frame(0), mention_author=False)
            for step in (1, 2):
                await asyncio.sleep(0.8)
                await message.edit(view=frame(step))
            await asyncio.sleep(0.8)
            counts = {k: reels.count(k) for k in set(reels)}
            top = max(counts.values())
            if top == 3:
                mult = next(s[3] for s in SLOT_SYMBOLS if s[0] == reels[0])
                payout = amount * mult
                note = f"Triple match pays **{mult}x**"
            elif top == 2:
                payout = int(amount * config.SLOT_PAIR_MULTIPLIER)
                note = f"A pair pays **{config.SLOT_PAIR_MULTIPLIER:g}x**"
            else:
                payout = 0
                note = "No match this time"
            lines = [f"{'  '.join(sym(r) for r in reels)}", f"- **Result:** {note}"]
            await self.conclude(ctx, amount, payout, "Slots", E.SLOT_SEVEN, lines, message)
        finally:
            self.end(ctx)

    @commands.hybrid_command(name="blackjack", aliases=["bj"], help="Play a hand of blackjack against me.")
    async def blackjack(self, ctx, bet: Optional[str] = None):
        amount = await self.begin(ctx, bet)
        if amount is None:
            return
        view = BlackjackView(self, ctx, amount)
        player = hand_value(view.player)
        dealer = hand_value(view.dealer)
        if player == 21:
            outcome = "push" if dealer == 21 else "blackjack"
            await view.finish(outcome)
            view.message = await ctx.reply(view=view, mention_author=False)
            return
        view.render_live()
        view.message = await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="rps", help="Play rock paper scissors for coins.")
    async def rps(self, ctx, bet: Optional[str] = None):
        amount = await self.begin(ctx, bet)
        if amount is None:
            return
        view = RpsView(self, ctx, amount)
        view.message = await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="roulette", aliases=["rl"], help="Bet on red, black, odd, even, green or a number.")
    async def roulette(self, ctx, bet: str, choice: str):
        pick = choice.lower()
        aliases = {"r": "red", "b": "black", "g": "green", "o": "odd", "e": "even"}
        pick = aliases.get(pick, pick)
        valid = pick in ("red", "black", "green", "odd", "even") or (pick.isdigit() and 0 <= int(pick) <= 36)
        if not valid:
            return await ui.notice(ctx, "err", "Choose `red`, `black`, `green`, `odd`, `even` or a number from 0 to 36.")
        amount = await self.begin(ctx, bet)
        if amount is None:
            return
        try:
            number = random.randint(0, 36)
            colour = "green" if number == 0 else "red" if number in REDS else "black"
            if pick == "green":
                won, mult = number == 0, 36
            elif pick in ("red", "black"):
                won, mult = colour == pick, 2
            elif pick in ("odd", "even"):
                won, mult = number != 0 and (number % 2 == 1) == (pick == "odd"), 2
            else:
                won, mult = number == int(pick), 36
            payout = amount * mult if won else 0
            lines = [f"- **You bet on:** {pick}", f"- **Ball landed on:** {number} ({colour})"]
            await self.conclude(ctx, amount, payout, "Roulette", E.DICE, lines)
        finally:
            self.end(ctx)

    @commands.hybrid_command(name="dice", aliases=["roll"], help="Roll two dice against me. Highest total wins.")
    async def dice(self, ctx, bet: Optional[str] = None):
        amount = await self.begin(ctx, bet)
        if amount is None:
            return
        try:
            mine = [random.randint(1, 6), random.randint(1, 6)]
            theirs = [random.randint(1, 6), random.randint(1, 6)]
            if sum(mine) > sum(theirs):
                payout = amount * 2
            elif sum(mine) == sum(theirs):
                payout = amount
            else:
                payout = 0
            lines = [
                f"- **You:** {mine[0]} + {mine[1]} = **{sum(mine)}**",
                f"- **{config.BOT_NAME}:** {theirs[0]} + {theirs[1]} = **{sum(theirs)}**",
            ]
            await self.conclude(ctx, amount, payout, "Dice Duel", E.DICE, lines)
        finally:
            self.end(ctx)


async def setup(bot):
    await bot.add_cog(Games(bot))
