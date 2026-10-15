import ast
import asyncio
import operator
import os
import platform
import re
import time
from typing import Optional

import discord
from discord.ext import commands

import config
from core import ui, utils
from core.base import LuniiCog
from core.emojis import E

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
DURATION = re.compile(r"(\d+)\s*([smhd])", re.I)
UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return UNARY[type(node.op)](safe_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        left, right = safe_eval(node.left), safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 10**9):
            raise ValueError("too large")
        return OPS[type(node.op)](left, right)
    raise ValueError("unsupported")


def memory_usage():
    try:
        with open("/proc/self/status") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    try:
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except Exception:
        return None


class Info(LuniiCog):
    category = "Info"
    groups = [
        ("Bot", ["botinfo", "ping", "uptime", "invite"]),
        ("Lookup", ["avatar", "banner", "userinfo", "serverinfo", "servericon", "membercount", "roleinfo"]),
        ("Tools", ["calc", "remind"]),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.reminders = {}
        self.tasks = set()

    async def cog_unload(self):
        for task in list(self.tasks):
            task.cancel()

    @commands.hybrid_command(name="ping", aliases=["latency"], help="Check how fast I am responding.")
    async def ping(self, ctx):
        start = time.perf_counter()
        await self.bot.db.fetchone("SELECT 1")
        db_ms = (time.perf_counter() - start) * 1000
        rows = [("Gateway", f"{self.bot.latency * 1000:.0f} ms", "ARROW"), ("Database", f"{db_ms:.1f} ms", "ARROW")]
        await ctx.reply(view=ui.Static(ui.head(E.CLOCK, "Pong!"), ui.sep(), ui.text(ui.bullets(rows))), mention_author=False)

    @commands.hybrid_command(name="uptime", help="See how long I have been online.")
    async def uptime(self, ctx):
        since = int(self.bot.started_at)
        rows = [("Online for", utils.duration(time.time() - self.bot.started_at), "ARROW"), ("Started", f"<t:{since}:F>", "ARROW")]
        await ctx.reply(view=ui.Static(ui.head(E.CLOCK, "Uptime"), ui.sep(), ui.text(ui.bullets(rows))), mention_author=False)

    @commands.hybrid_command(name="botinfo", aliases=["stats", "about"], help="See my live statistics.")
    async def botinfo(self, ctx):
        totals = await self.bot.db.overview()
        users = sum(g.member_count or 0 for g in self.bot.guilds)
        total_commands = len({c.qualified_name for c in self.bot.commands if not c.hidden})
        memory = memory_usage()
        try:
            db_size = os.path.getsize(config.DATABASE_PATH) / (1024 * 1024)
        except OSError:
            db_size = 0
        prefix = self.bot.prefix_for(ctx.guild)

        def overview():
            rows = [
                ("Servers", utils.fmt(len(self.bot.guilds)), "ARROW"),
                ("Members", utils.fmt(users), "ARROW"),
                ("Commands", utils.fmt(total_commands), "ARROW"),
                ("Prefix", f"`{prefix}`", "ARROW"),
                ("Uptime", utils.duration(time.time() - self.bot.started_at), "ARROW"),
                ("Latency", f"{self.bot.latency * 1000:.0f} ms", "ARROW"),
            ]
            header = f"### {E.LOGO} {config.BOT_NAME} Info\n{config.TAGLINE}\n\n{ui.bullets(rows)}"
            return [ui.section(header, self.bot.user.display_avatar.url)]

        def economy():
            rows = [
                ("Players", utils.fmt(totals["users"]), "PAW"),
                ("Coins in circulation", utils.fmt(totals["coins"]), "COIN"),
                ("Total won", utils.fmt(totals["won"]), "TROPHY"),
                ("Total lost", utils.fmt(totals["lost"]), "DICE"),
                ("Catches held", utils.fmt(totals["catches"]), "FISH"),
                ("Commands used", utils.fmt(totals["commands"]), "GAMES"),
            ]
            return [ui.head(E.COIN, "Economy"), ui.sep(), ui.text(ui.bullets(rows))]

        def system():
            rows = [
                ("Python", platform.python_version(), "ARROW"),
                ("discord.py", discord.__version__, "ARROW"),
                ("Version", f"{config.VERSION}", "ARROW"),
                ("Memory", f"{memory:.1f} MB" if memory else "Unknown", "ARROW"),
                ("Database", f"{db_size:.2f} MB", "ARROW"),
                ("Platform", f"{platform.system()} {platform.machine()}", "ARROW"),
            ]
            return [ui.head(E.SETTINGS, "System"), ui.sep(), ui.text(ui.bullets(rows))]

        links = ui.link_buttons(invite=self.bot.invite_url)
        view = ui.PageView(ctx, [overview, economy, system], links=links)
        view.message = await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="invite", aliases=["support"], help="Get my invite and support links.")
    async def invite(self, ctx):
        buttons = ui.link_buttons(invite=self.bot.invite_url)
        view = ui.Static(
            ui.head(E.LOGO, f"Invite {config.BOT_NAME}"),
            ui.text("Bring me to your server and start playing."),
            ui.sep(),
            ui.row(*buttons),
        )
        await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="avatar", aliases=["av", "pfp"], help="Show someone's avatar in full size.")
    async def avatar(self, ctx, user: Optional[discord.User] = None):
        target = user or ctx.author
        url = target.display_avatar.with_size(1024).url
        await ctx.reply(view=ui.Static(ui.head(E.INFO, f"{target.display_name}'s Avatar"), ui.gallery(url)), mention_author=False)

    @commands.hybrid_command(name="banner", help="Show someone's profile banner.")
    async def banner(self, ctx, user: Optional[discord.User] = None):
        target = user or ctx.author
        full = await self.bot.fetch_user(target.id)
        if full.banner is None:
            return await ui.notice(ctx, "warn", f"{target.display_name} doesn't have a banner.")
        await ctx.reply(view=ui.Static(ui.head(E.INFO, f"{target.display_name}'s Banner"), ui.gallery(full.banner.with_size(1024).url)), mention_author=False)

    @commands.hybrid_command(name="userinfo", aliases=["ui", "whois"], help="Show details about a member.")
    async def userinfo(self, ctx, user: Optional[discord.User] = None):
        target = user or ctx.author
        rows = [
            ("Username", str(target), "ARROW"),
            ("ID", f"`{target.id}`", "ARROW"),
            ("Created", f"<t:{int(target.created_at.timestamp())}:D>", "ARROW"),
        ]
        member = ctx.guild.get_member(target.id) if ctx.guild else None
        if member and member.joined_at:
            rows.append(("Joined", f"<t:{int(member.joined_at.timestamp())}:D>", "ARROW"))
        if member and len(member.roles) > 1:
            rows.append(("Top role", member.top_role.mention, "ARROW"))
        if target.bot:
            rows.append(("Type", "Bot", "ARROW"))
        header = f"### {E.INFO} {target.display_name}\n\n{ui.bullets(rows)}"
        await ctx.reply(view=ui.Static(ui.section(header, target.display_avatar.url)), mention_author=False)

    @commands.hybrid_command(name="serverinfo", aliases=["si", "guildinfo"], help="Show details about this server.")
    @commands.guild_only()
    async def serverinfo(self, ctx):
        guild = ctx.guild
        general = [
            ("ID", f"`{guild.id}`", "ARROW"),
            ("Owner", f"<@{guild.owner_id}>", "ARROW"),
            ("Created", f"<t:{int(guild.created_at.timestamp())}:D>", "ARROW"),
        ]
        counts = [
            ("Members", utils.fmt(guild.member_count or 0), "ARROW"),
            ("Channels", f"{len(guild.text_channels)} text, {len(guild.voice_channels)} voice", "ARROW"),
            ("Roles", len(guild.roles), "ARROW"),
            ("Boosts", guild.premium_subscription_count, "ARROW"),
        ]
        header = f"### {E.INFO} {guild.name}\n\n{ui.bullets(general)}"
        top = ui.section(header, guild.icon.url) if guild.icon else ui.text(header)
        view = ui.Static(top, ui.sep(), ui.text(ui.block("Overview", ui.bullets(counts))))
        await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="servericon", aliases=["guildicon"], help="Show this server's icon.")
    @commands.guild_only()
    async def servericon(self, ctx):
        if ctx.guild.icon is None:
            return await ui.notice(ctx, "warn", "This server has no icon.")
        await ctx.reply(view=ui.Static(ui.head(E.INFO, f"{ctx.guild.name} Icon"), ui.gallery(ctx.guild.icon.with_size(1024).url)), mention_author=False)

    @commands.hybrid_command(name="membercount", aliases=["mc"], help="Show how many members this server has.")
    @commands.guild_only()
    async def membercount(self, ctx):
        rows = [("Members", utils.fmt(ctx.guild.member_count or 0), "PAW"), ("Boosts", ctx.guild.premium_subscription_count, "STAR")]
        await ctx.reply(view=ui.Static(ui.head(E.INFO, ctx.guild.name), ui.sep(), ui.text(ui.bullets(rows))), mention_author=False)

    @commands.hybrid_command(name="roleinfo", aliases=["ri"], help="Show details about a role.")
    @commands.guild_only()
    async def roleinfo(self, ctx, role: discord.Role):
        rows = [
            ("ID", f"`{role.id}`", "ARROW"),
            ("Colour", str(role.colour), "ARROW"),
            ("Position", role.position, "ARROW"),
            ("Mentionable", "Yes" if role.mentionable else "No", "ARROW"),
            ("Hoisted", "Yes" if role.hoist else "No", "ARROW"),
            ("Created", f"<t:{int(role.created_at.timestamp())}:D>", "ARROW"),
        ]
        await ctx.reply(view=ui.Static(ui.head(E.INFO, role.name), ui.sep(), ui.text(ui.bullets(rows))), mention_author=False)

    @commands.hybrid_command(name="calc", aliases=["calculate", "math"], help="Solve a math expression.")
    async def calc(self, ctx, *, expression: str):
        cleaned = expression.replace("^", "**").replace("x", "*").replace("\u00d7", "*").replace("\u00f7", "/").replace(",", "")
        try:
            result = safe_eval(ast.parse(cleaned.strip(), mode="eval"))
        except ZeroDivisionError:
            return await ui.notice(ctx, "err", "You can't divide by zero.")
        except Exception:
            return await ui.notice(ctx, "err", "I couldn't solve that. Use numbers with `+ - * / % ** ( )`.")
        if isinstance(result, float):
            result = int(result) if result.is_integer() else round(result, 10)
        shown = f"{result:,}" if isinstance(result, int) else str(result)
        rows = [("Input", f"`{expression[:200]}`"), ("Result", f"**{shown[:200]}**")]
        await ctx.reply(view=ui.Static(ui.head(E.CHART, "Calculator"), ui.sep(), ui.text(ui.bullets(rows))), mention_author=False)

    @commands.hybrid_command(name="remind", aliases=["reminder"], help="Set a reminder like 10m, 2h or 1h30m.")
    async def remind(self, ctx, when: str, *, reminder: str = "Time is up!"):
        parts = DURATION.findall(when)
        if not parts or "".join(f"{n}{u}" for n, u in parts).lower() != when.lower().replace(" ", ""):
            return await ui.notice(ctx, "err", "Use a time like `10m`, `2h` or `1h30m`.")
        seconds = sum(int(n) * UNITS[u.lower()] for n, u in parts)
        if not 5 <= seconds <= 86400:
            return await ui.notice(ctx, "err", "Reminders can be between 5 seconds and 24 hours.")
        if self.reminders.get(ctx.author.id, 0) >= 5:
            return await ui.notice(ctx, "warn", "You already have 5 active reminders.")
        self.reminders[ctx.author.id] = self.reminders.get(ctx.author.id, 0) + 1
        task = asyncio.create_task(self.fire(ctx.author, ctx.channel, seconds, reminder[:300]))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        await ui.notice(ctx, "ok", f"I'll remind you {utils.ts(seconds)} {E.CLOCK}")

    async def fire(self, user, channel, seconds, text):
        try:
            await asyncio.sleep(seconds)
            await channel.send(
                f"{user.mention} {E.CLOCK} Reminder: {text}",
                allowed_mentions=discord.AllowedMentions(users=[user]),
            )
        except (discord.HTTPException, asyncio.CancelledError):
            pass
        finally:
            self.reminders[user.id] = max(0, self.reminders.get(user.id, 1) - 1)


async def setup(bot):
    await bot.add_cog(Info(bot))
