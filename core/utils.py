import re
import time

from discord.ext import commands

import config

SUFFIXES = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
NUMBER = re.compile(r"^(\d+(?:\.\d+)?)([kmb]?)$")


def fmt(n):
    return f"{int(n):,}"


def parse_amount(raw, available, *, maximum=None, minimum=1):
    s = str(raw).lower().replace(",", "").replace("_", "").strip()
    capped = False
    if s in ("all", "max"):
        value = available
        capped = True
    elif s == "half":
        value = available // 2
        capped = True
    elif s.endswith("%"):
        try:
            pct = float(s[:-1])
        except ValueError:
            raise commands.BadArgument("That is not a valid percentage.")
        if not 0 < pct <= 100:
            raise commands.BadArgument("Percentages must be between 1 and 100.")
        value = int(available * pct / 100)
        capped = True
    else:
        match = NUMBER.match(s)
        if not match:
            raise commands.BadArgument("Enter a number like `500`, `2.5k`, `half` or `all`.")
        value = int(float(match.group(1)) * SUFFIXES.get(match.group(2), 1))
        if value > available:
            raise commands.BadArgument(f"You only have **{fmt(available)}** {config.CURRENCY} available.")
    if maximum is not None and value > maximum:
        if capped:
            value = maximum
        else:
            raise commands.BadArgument(f"The maximum amount here is **{fmt(maximum)}** {config.CURRENCY}.")
    if value < minimum:
        raise commands.BadArgument(f"The minimum amount is **{fmt(minimum)}** {config.CURRENCY}.")
    return value


class Cash(commands.Converter):
    async def convert(self, ctx, argument):
        row = await ctx.bot.db.user(ctx.author.id)
        return parse_amount(argument, row["cash"])


class Bet(commands.Converter):
    async def convert(self, ctx, argument):
        row = await ctx.bot.db.user(ctx.author.id)
        return parse_amount(argument, row["cash"], maximum=config.MAX_BET)


class DepositAmount(commands.Converter):
    async def convert(self, ctx, argument):
        row = await ctx.bot.db.user(ctx.author.id)
        room = max(0, row["bank_cap"] - row["bank"])
        s = argument.lower().strip()
        relative = s in ("all", "max", "half") or s.endswith("%")
        return parse_amount(argument, min(row["cash"], room) if relative else row["cash"])


class WithdrawAmount(commands.Converter):
    async def convert(self, ctx, argument):
        row = await ctx.bot.db.user(ctx.author.id)
        return parse_amount(argument, row["bank"])


def duration(seconds):
    seconds = int(seconds)
    parts = []
    for label, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if seconds >= size:
            parts.append(f"{seconds // size}{label}")
            seconds %= size
    return " ".join(parts[:3]) or "0s"


def ts(seconds_from_now, style="R"):
    return f"<t:{int(time.time() + seconds_from_now)}:{style}>"


def bar(current, total, width=10, full="\u25b0", empty="\u25b1"):
    if total <= 0:
        return empty * width
    filled = max(0, min(width, int(round(width * current / total))))
    return full * filled + empty * (width - filled)
