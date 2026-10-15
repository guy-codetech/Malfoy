import logging
import random
import time
from collections import Counter
from typing import Optional

import discord
from discord import ui as dui
from discord.ext import commands

import config
from core import cards, data, ui, utils
from core.base import LuniiCog
from core.database import level_for, xp_for
from core.emojis import E
from core.utils import Cash, fmt

log = logging.getLogger("lunii.economy")


class LeaderboardView(ui.Layout):
    def __init__(self, cog, ctx):
        super().__init__(author=ctx.author, timeout=120)
        self.cog = cog
        self.ctx = ctx
        self.kind = "networth"

    async def name_of(self, uid):
        user = self.cog.bot.get_user(uid)
        if user is None:
            try:
                user = await self.cog.bot.fetch_user(uid)
            except discord.HTTPException:
                return "Unknown User"
        return user.display_name

    async def build(self):
        db = self.cog.bot.db
        rows = await db.leaderboard(self.kind, 10)
        titles = {"cash": "Richest in Cash", "networth": "Highest Net Worth", "level": "Highest Level", "streak": "Longest Streak"}
        lines = []
        for index, row in enumerate(rows, 1):
            name = await self.name_of(row["user_id"])
            if self.kind == "level":
                value = f"Level {level_for(row['value'])}"
            elif self.kind == "streak":
                value = f"{fmt(row['value'])} days"
            else:
                value = f"{fmt(row['value'])} {E.COIN}"
            lines.append(f"- **{index}.** {name} {E.ARROW} {value}")
        if not lines:
            lines.append("Nobody is on the board yet. Be the first!")
        rank = await db.rank(self.ctx.author.id, self.kind)
        options = [
            discord.SelectOption(label="Net Worth", value="networth", emoji=ui.emoji_or_none("CHART"), default=self.kind == "networth"),
            discord.SelectOption(label="Cash", value="cash", emoji=ui.emoji_or_none("COIN"), default=self.kind == "cash"),
            discord.SelectOption(label="Level", value="level", emoji=ui.emoji_or_none("STAR"), default=self.kind == "level"),
            discord.SelectOption(label="Daily Streak", value="streak", emoji=ui.emoji_or_none("GIFT"), default=self.kind == "streak"),
        ]
        select = dui.Select(placeholder="Switch leaderboard", options=options)
        select.callback = self.on_select
        self.clear_items()
        self.add_item(
            ui.card(
                ui.head(E.TROPHY, titles[self.kind]),
                ui.sep(),
                ui.text("\n".join(lines)),
                ui.sep(),
                ui.text(f"__**Your Rank**__\n- **Position:** #{fmt(rank)}"),
                ui.sep(),
                ui.row(select),
            )
        )

    async def on_select(self, interaction):
        self.kind = interaction.data["values"][0]
        await self.build()
        await interaction.response.edit_message(view=self)


class Economy(LuniiCog):
    category = "Economy"
    groups = [
        ("Earn", ["daily", "work", "beg", "crime", "rob", "pay"]),
        ("Profile", ["balance", "profile", "rank", "leaderboard"]),
        ("Collect", ["hunt", "fish", "zoo", "sell"]),
        ("Shop", ["shop", "buy", "inventory", "use"]),
    ]

    def panel(self, *children, accent=None):
        return ui.Static(*children, accent=accent)

    async def avatar_bytes(self, user):
        try:
            return await user.display_avatar.replace(size=256, format="png").read()
        except discord.HTTPException:
            return b""

    async def card_reply(self, ctx, fn, args, fallback, extra=None):
        if config.CARDS_ENABLED:
            try:
                png = await cards.render(fn, *args)
                children = [ui.gallery("attachment://card.png")] + list(extra or [])
                return await ctx.reply(view=ui.Static(*children), files=[ui.image_file(png)], mention_author=False)
            except Exception:
                log.exception("Card rendering failed, using text fallback")
        await ctx.reply(view=ui.Static(*fallback), mention_author=False)

    @commands.hybrid_command(name="balance", aliases=["bal", "cash", "wallet"], help="Check your wallet and bank.")
    async def balance(self, ctx, user: Optional[discord.User] = None):
        target = user or ctx.author
        if target.bot:
            return await ui.notice(ctx, "err", "Bots don't carry wallets.")
        row = await self.bot.db.user(target.id)
        avatar = await self.avatar_bytes(target)
        fallback = [
            ui.head(E.COIN, f"{target.display_name}'s Wallet"),
            ui.sep(),
            ui.text(
                ui.bullets(
                    [
                        ("Cash", fmt(row["cash"]), "COIN"),
                        ("Bank", f"{fmt(row['bank'])} / {fmt(row['bank_cap'])}", "BANK"),
                        ("Net Worth", fmt(row["cash"] + row["bank"]), "CHART"),
                    ]
                )
            ),
        ]
        await self.card_reply(
            ctx, cards.wallet_card, (target.display_name, avatar, row["cash"], row["bank"], row["bank_cap"], row["level"]), fallback
        )

    @commands.hybrid_command(name="profile", aliases=["me"], help="View a detailed profile card.")
    async def profile(self, ctx, user: Optional[discord.User] = None):
        target = user or ctx.author
        if target.bot:
            return await ui.notice(ctx, "err", "Bots don't have profiles.")
        row = await self.bot.db.user(target.id)
        owned = sum((await self.bot.db.items("catches", target.id)).values())
        rank = await self.bot.db.rank(target.id, "level")
        level = row["level"]
        floor, ceil = xp_for(level), xp_for(level + 1)
        avatar = await self.avatar_bytes(target)
        since = time.strftime("%b %d, %Y", time.gmtime(row["created"]))
        fallback = [
            ui.head(E.PAW, target.display_name),
            ui.sep(),
            ui.text(
                ui.bullets(
                    [
                        ("Level", f"{level} ({fmt(row['xp'])} / {fmt(ceil)} xp)", "STAR"),
                        ("Cash", fmt(row["cash"]), "COIN"),
                        ("Bank", f"{fmt(row['bank'])} / {fmt(row['bank_cap'])}", "BANK"),
                        ("Streak", f"{row['streak']} days", "GIFT"),
                        ("Won / Lost", f"{fmt(row['won'])} / {fmt(row['lost'])}", "DICE"),
                        ("Catches", fmt(owned), "PAW"),
                    ]
                )
            ),
        ]
        await self.card_reply(
            ctx,
            cards.profile_card,
            (target.display_name, avatar, level, rank, row["xp"], floor, ceil, row["cash"], row["bank"], row["streak"], row["won"], row["lost"], owned, since),
            fallback,
        )

    @commands.hybrid_command(name="rank", aliases=["xp", "level"], help="Show your level and xp card.")
    async def rank(self, ctx, user: Optional[discord.User] = None):
        target = user or ctx.author
        if target.bot:
            return await ui.notice(ctx, "err", "Bots don't earn xp.")
        row = await self.bot.db.user(target.id)
        rank = await self.bot.db.rank(target.id, "level")
        level = row["level"]
        floor, ceil = xp_for(level), xp_for(level + 1)
        avatar = await self.avatar_bytes(target)
        fallback = [
            ui.head(E.STAR, f"{target.display_name}'s Level"),
            ui.sep(),
            ui.text(
                ui.bullets(
                    [
                        ("Level", level),
                        ("Rank", f"#{fmt(rank)}"),
                        ("XP", f"{fmt(row['xp'])} / {fmt(ceil)} {utils.bar(row['xp'] - floor, ceil - floor)}"),
                    ]
                )
            ),
        ]
        await self.card_reply(ctx, cards.rank_card, (target.display_name, avatar, level, rank, row["xp"], floor, ceil), fallback)

    @commands.hybrid_command(name="daily", help="Claim your daily reward and keep your streak alive.")
    async def daily(self, ctx):
        row = await self.bot.db.user(ctx.author.id)
        now = time.time()
        since = now - row["last_daily"]
        window = config.COOLDOWNS["daily"]
        if row["last_daily"] and since < window:
            return await ui.notice(ctx, "warn", f"Your daily is ready {utils.ts(window - since)}.")
        streak = row["streak"] + 1 if row["last_daily"] and since < config.DAILY_WINDOW else 1
        reward = config.DAILY_BASE + min(streak, config.DAILY_STREAK_MAX) * config.DAILY_STREAK_BONUS
        interest = min(int(row["bank"] * config.BANK_INTEREST_RATE), config.BANK_INTEREST_MAX)
        interest = min(interest, max(0, row["bank_cap"] - row["bank"]))
        await self.bot.db.claim_daily(ctx.author.id, reward, streak, interest)
        rows = [
            ("Reward", f"+{fmt(reward)} {config.CURRENCY}", "COIN"),
            ("Streak", f"{streak} day{'s' if streak != 1 else ''} {utils.bar(min(streak, 30), 30)}", "STAR"),
        ]
        if interest:
            rows.append(("Bank interest", f"+{fmt(interest)} {config.CURRENCY}", "BANK"))
        view = self.panel(
            ui.head(E.GIFT, "Daily Reward"),
            ui.sep(),
            ui.text(ui.bullets(rows)),
            ui.sep(),
            ui.text(f"Come back {utils.ts(window)} to keep the streak going."),
            accent=config.ACCENT_OK,
        )
        await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="work", help="Do a quick job for some coins.")
    async def work(self, ctx):
        if not await self.cooldown(ctx, "work"):
            return
        row = await self.bot.db.user(ctx.author.id)
        pay = random.randint(*config.WORK_RANGE) + row["level"] * 5
        await self.bot.db.add_cash(ctx.author.id, pay)
        job = random.choice(data.JOBS)
        view = self.panel(
            ui.head(E.HAMMER, "Work"),
            ui.sep(),
            ui.text(f"You {job}.\n- **Earned:** {fmt(pay)} {config.CURRENCY} {E.COIN}"),
            accent=config.ACCENT_OK,
        )
        await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="beg", help="Ask kind strangers for a few coins.")
    async def beg(self, ctx):
        if not await self.cooldown(ctx, "beg"):
            return
        if random.random() < config.BEG_CHANCE:
            amount = random.randint(*config.BEG_RANGE)
            await self.bot.db.add_cash(ctx.author.id, amount)
            await ui.notice(ctx, "ok", f"{random.choice(data.BEG_LINES)}: **{fmt(amount)}** {config.CURRENCY} {E.COIN}")
        else:
            await ui.notice(ctx, "warn", random.choice(data.BEG_FAILS))

    @commands.hybrid_command(name="crime", help="Take a risky shot at a big payout.")
    async def crime(self, ctx):
        if not await self.cooldown(ctx, "crime"):
            return
        if random.random() < config.CRIME_CHANCE:
            amount = random.randint(*config.CRIME_WIN)
            await self.bot.db.add_cash(ctx.author.id, amount)
            await ui.notice(ctx, "ok", f"You {random.choice(data.CRIME_WINS)} and pocketed **{fmt(amount)}** {config.CURRENCY} {E.COIN}")
        else:
            row = await self.bot.db.user(ctx.author.id)
            fine = min(row["cash"], random.randint(*config.CRIME_LOSS))
            await self.bot.db.add_cash(ctx.author.id, -fine)
            await self.bot.db.record(ctx.author.id, -fine)
            await ui.notice(ctx, "err", f"You {random.choice(data.CRIME_FAILS)}. Fine paid: **{fmt(fine)}** {config.CURRENCY}")

    @commands.hybrid_command(name="rob", help="Try to steal cash from another member.")
    async def rob(self, ctx, user: discord.User):
        if user.bot or user.id == ctx.author.id:
            return await ui.notice(ctx, "err", "Pick another human to rob.")
        me = await self.bot.db.user(ctx.author.id)
        target = await self.bot.db.user(user.id)
        if me["cash"] < 100:
            return await ui.notice(ctx, "err", f"You need at least **100** {config.CURRENCY} in your wallet to attempt a robbery.")
        if target["cash"] < config.ROB_MIN_TARGET_CASH:
            return await ui.notice(ctx, "warn", f"{user.display_name} isn't carrying enough cash to be worth it.")
        if not await self.cooldown(ctx, "rob"):
            return
        if await self.bot.db.take_item("inventory", user.id, "padlock"):
            fine = min(me["cash"], random.randint(*config.ROB_FINE))
            await self.bot.db.transfer(ctx.author.id, user.id, fine)
            return await ui.notice(ctx, "err", f"{user.display_name}'s {E.LOCK} padlock held firm. You were fined **{fmt(fine)}** {config.CURRENCY}.")
        if random.random() < config.ROB_CHANCE:
            steal = max(1, int(target["cash"] * random.uniform(*config.ROB_STEAL_RATIO)))
            if not await self.bot.db.transfer(user.id, ctx.author.id, steal):
                return await ui.notice(ctx, "warn", "They spent their cash before you could grab it.")
            await ui.notice(ctx, "ok", f"You swiped **{fmt(steal)}** {config.CURRENCY} {E.COIN} from {user.display_name}!")
        else:
            fine = min(me["cash"], random.randint(*config.ROB_FINE))
            await self.bot.db.transfer(ctx.author.id, user.id, fine)
            await ui.notice(ctx, "err", f"You got caught and paid **{fmt(fine)}** {config.CURRENCY} to {user.display_name}.")

    @commands.hybrid_command(name="pay", aliases=["give", "send"], help="Send coins to another member.")
    async def pay(self, ctx, user: discord.User, amount: Cash):
        if user.bot or user.id == ctx.author.id:
            return await ui.notice(ctx, "err", "Pick another human to pay.")
        if not await self.bot.db.transfer(ctx.author.id, user.id, amount):
            return await ui.notice(ctx, "err", "You don't have enough cash for that.")
        await ui.notice(ctx, "ok", f"Sent **{fmt(amount)}** {config.CURRENCY} {E.COIN} to {user.display_name}.")

    @commands.hybrid_command(name="leaderboard", aliases=["lb", "top"], help="See the richest and highest level members.")
    async def leaderboard(self, ctx):
        view = LeaderboardView(self, ctx)
        await view.build()
        view.message = await ctx.reply(view=view, mention_author=False)

    async def go_catch(self, ctx, kind, cost, key, title, icon, verb):
        row = await self.bot.db.user(ctx.author.id)
        if row["cash"] < cost:
            return await ui.notice(ctx, "err", f"You need **{cost}** {config.CURRENCY} to {verb}.")
        if not await self.cooldown(ctx, key):
            return
        if not await self.bot.db.take_cash(ctx.author.id, cost):
            return await ui.notice(ctx, "err", f"You need **{cost}** {config.CURRENCY} to {verb}.")
        lucky = await self.bot.db.take_item("inventory", ctx.author.id, "lucky_charm")
        count = 1 + (random.random() < 0.35) + (random.random() < 0.1)
        found = [data.roll_catch(kind, lucky) for _ in range(count)]
        await self.bot.db.add_items("catches", ctx.author.id, dict(Counter(c["id"] for c in found)))
        lines = [f"- **{i['name']}** ({data.RARITY_LABEL[i['rarity']]}) worth {fmt(i['value'])} {E.COIN}" for i in found]
        footer = f"Cost {cost} {config.CURRENCY}"
        if lucky:
            footer += f" and a {E.STAR} Lucky Charm"
        view = self.panel(ui.head(icon, title), ui.sep(), ui.text("\n".join(lines)), ui.sep(), ui.text(footer))
        await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="hunt", help="Go hunting and add animals to your zoo.")
    async def hunt(self, ctx):
        await self.go_catch(ctx, "hunt", config.HUNT_COST, "hunt", "Hunt", E.PAW, "hunt")

    @commands.hybrid_command(name="fish", aliases=["fishing"], help="Cast a line and catch some fish.")
    async def fish(self, ctx):
        await self.go_catch(ctx, "fish", config.FISH_COST, "fish", "Fishing", E.FISH, "fish")

    @commands.hybrid_command(name="zoo", aliases=["pets", "catches"], help="Show your collection of animals and fish.")
    async def zoo(self, ctx, user: Optional[discord.User] = None):
        target = user or ctx.author
        if target.bot:
            return await ui.notice(ctx, "err", "Bots don't keep zoos.")
        owned = await self.bot.db.items("catches", target.id)
        total_value = sum(data.CATCHES[i]["value"] * q for i, q in owned.items() if i in data.CATCHES)
        header = ui.section(f"### {E.PAW} {target.display_name}'s Zoo", target.display_avatar.url)
        children = [header]
        prefix = self.bot.prefix_for(ctx.guild)
        if not owned:
            children.append(ui.text(f"Empty for now. Try `{prefix}hunt` or `{prefix}fish`."))
        else:
            for rarity in reversed(data.RARITY_ORDER):
                names = [
                    f"{data.CATCHES[i]['name']} x{q}"
                    for i, q in sorted(owned.items())
                    if i in data.CATCHES and data.CATCHES[i]["rarity"] == rarity
                ]
                if names:
                    children += [ui.sep(), ui.text(ui.block(data.RARITY_LABEL[rarity], ", ".join(names)))]
        discovered = len([i for i in owned if i in data.CATCHES])
        children += [
            ui.sep(),
            ui.text(ui.bullets([("Species", f"{discovered} / {len(data.CATCHES)}", "PAW"), ("Worth", f"{fmt(total_value)} {config.CURRENCY}", "COIN")])),
        ]
        await ctx.reply(view=self.panel(*children), mention_author=False)

    @commands.hybrid_command(name="sell", help="Sell your catches. Use all, a rarity, animals, fish or a name.")
    async def sell(self, ctx, what: str = "all", amount: Optional[int] = None):
        owned = await self.bot.db.items("catches", ctx.author.id)
        if not owned:
            return await ui.notice(ctx, "warn", "You have nothing to sell yet.")
        key = what.lower().replace(" ", "_")
        selection = {}
        if key == "all":
            selection = dict(owned)
        elif key in data.RARITY_ORDER:
            selection = {i: q for i, q in owned.items() if data.CATCHES[i]["rarity"] == key}
        elif key in ("animals", "animal", "hunt"):
            selection = {i: q for i, q in owned.items() if data.CATCHES[i]["kind"] == "hunt"}
        elif key in ("fish", "fishes"):
            selection = {i: q for i, q in owned.items() if data.CATCHES[i]["kind"] == "fish"}
        elif key in data.CATCHES and key in owned:
            qty = owned[key] if amount is None else max(1, min(amount, owned[key]))
            selection = {key: qty}
        if not selection:
            return await ui.notice(ctx, "err", "I couldn't find anything to sell with that name.")
        total = sum(data.CATCHES[i]["value"] * q for i, q in selection.items())
        count = sum(selection.values())
        if not await self.bot.db.sell_catches(ctx.author.id, selection, total):
            return await ui.notice(ctx, "err", "Your collection changed while selling. Please try again.")
        await ui.notice(ctx, "ok", f"Sold **{fmt(count)}** catch{'es' if count != 1 else ''} for **{fmt(total)}** {config.CURRENCY} {E.COIN}")

    @commands.hybrid_command(name="shop", aliases=["store"], help="Browse items you can buy.")
    async def shop(self, ctx):
        prefix = self.bot.prefix_for(ctx.guild)
        items = [{"name": i["name"], "price": i["price"], "icon": i["icon"]} for i in data.SHOP.values()]
        rows = [f"- {E(i['icon'])} **{i['name']}:** {i['desc']}".replace("-  ", "- ") for i in data.SHOP.values()]
        details = [ui.sep(), ui.text("\n".join(rows)), ui.sep(), ui.text(f"Buy with `{prefix}buy <item> [amount]`")]
        fallback = [ui.head(E.BAG, "Shop"), ui.sep()] + [
            ui.text("\n".join(f"- {E(i['icon'])} **{i['name']}** {E.ARROW} {fmt(i['price'])} {E.COIN}\n  {i['desc']}".replace("-  ", "- ") for i in data.SHOP.values()))
        ] + details[2:]
        await self.card_reply(ctx, cards.shop_card, (items,), fallback, extra=details)

    @commands.hybrid_command(name="buy", help="Buy an item from the shop.")
    async def buy(self, ctx, item: str, quantity: int = 1):
        key = data.find_shop_item(item)
        if key is None:
            return await ui.notice(ctx, "err", "That item isn't in the shop.")
        if not 1 <= quantity <= 100:
            return await ui.notice(ctx, "err", "You can buy between 1 and 100 at a time.")
        info = data.SHOP[key]
        cost = info["price"] * quantity
        if not await self.bot.db.take_cash(ctx.author.id, cost):
            return await ui.notice(ctx, "err", f"You need **{fmt(cost)}** {config.CURRENCY} for that.")
        await self.bot.db.add_item("inventory", ctx.author.id, key, quantity)
        await ui.notice(ctx, "ok", f"Bought **{quantity}x {info['name']}** for **{fmt(cost)}** {config.CURRENCY} {E(info['icon'])}")

    @commands.hybrid_command(name="inventory", aliases=["inv", "bag"], help="See the items you own.")
    async def inventory(self, ctx):
        items = await self.bot.db.items("inventory", ctx.author.id)
        rows = []
        for key, qty in sorted(items.items()):
            info = data.SHOP.get(key)
            if info:
                rows.append((info["name"], f"x{qty}", info["icon"]))
        body = ui.bullets(rows) if rows else "Nothing here yet. Visit the shop!"
        await ctx.reply(view=self.panel(ui.head(E.BAG, f"{ctx.author.display_name}'s Inventory"), ui.sep(), ui.text(body)), mention_author=False)

    @commands.hybrid_command(name="use", help="Use an item such as a lootbox or bank note.")
    async def use(self, ctx, item: str, quantity: int = 1):
        key = data.find_shop_item(item)
        if key is None:
            return await ui.notice(ctx, "err", "I don't know that item.")
        if key in ("padlock", "lucky_charm"):
            return await ui.notice(ctx, "info", f"**{data.SHOP[key]['name']}** works automatically when it's needed.")
        if not 1 <= quantity <= 25:
            return await ui.notice(ctx, "err", "You can use between 1 and 25 at a time.")
        if not await self.bot.db.take_item("inventory", ctx.author.id, key, quantity):
            return await ui.notice(ctx, "err", "You don't own enough of that item.")
        if key == "lootbox":
            values, weights = zip(*data.LOOT_TABLE)
            total = sum(random.choices(values, weights=weights, k=quantity))
            await self.bot.db.add_cash(ctx.author.id, total)
            return await ui.notice(ctx, "ok", f"{E.GIFT} Opened **{quantity}** lootbox{'es' if quantity != 1 else ''} and found **{fmt(total)}** {config.CURRENCY}!")
        await self.bot.db.add_bank_cap(ctx.author.id, 10000 * quantity)
        await ui.notice(ctx, "ok", f"{E.BANK} Your bank capacity grew by **{fmt(10000 * quantity)}**.")


async def setup(bot):
    await bot.add_cog(Economy(bot))
