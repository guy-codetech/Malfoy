import hashlib
import random
import time
from typing import Optional

import discord
from discord import app_commands
from discord import ui as dui
from discord.ext import commands

import config
from core import data, ui
from core.base import MalfoyCog
from core.emojis import E
from core.utils import bar

TARGETED = {
    "hug": "hugs",
    "kiss": "kisses",
    "pat": "pats",
    "slap": "slaps",
    "bite": "bites",
    "cuddle": "cuddles",
    "poke": "pokes",
    "lick": "licks",
    "tickle": "tickles",
    "punch": "punches",
    "smack": "smacks",
    "handhold": "holds hands with",
    "nuzzle": "nuzzles",
    "pinch": "pinches",
    "wink": "winks at",
    "wave": "waves at",
    "stare": "stares at",
    "angrystare": "glares at",
    "airkiss": "blows a kiss to",
    "brofist": "fist bumps",
}

SOLO = {
    "blush": "blushes",
    "cry": "cries",
    "dance": "dances",
    "happy": "is feeling happy",
    "laugh": "laughs",
    "pout": "pouts",
    "sad": "feels sad",
    "shy": "is feeling shy",
    "sleep": "falls asleep",
    "smile": "smiles",
    "smug": "looks smug",
    "yawn": "yawns",
    "nervous": "is nervous",
    "scared": "is scared",
    "sigh": "sighs",
    "tired": "is tired",
    "shrug": "shrugs",
    "facepalm": "facepalms",
    "clap": "claps",
    "slowclap": "slow claps",
    "cheers": "raises a toast",
    "celebrate": "celebrates",
    "evillaugh": "laughs evilly",
    "drool": "drools",
    "headbang": "headbangs",
    "love": "is in love",
    "nom": "munches happily",
    "surprised": "is surprised",
    "yay": "cheers with joy",
    "thumbsup": "gives a thumbs up",
    "sorry": "says sorry",
    "run": "runs away",
    "mad": "is mad",
    "shout": "shouts",
    "sing": "sings a song",
}

ALL_ACTIONS = {**TARGETED, **SOLO}


class RoleplayView(ui.Layout):
    def __init__(self, cog, action, verb, gif, author, target, count, can_return):
        super().__init__(author=None, timeout=300)
        self.cog = cog
        self.action = action
        self.verb = verb
        self.gif = gif
        self.source = author
        self.target = target
        self.count = count
        self.button = None
        if can_return:
            self.button = dui.Button(style=discord.ButtonStyle.secondary, label=f"{action.title()} back")
            self.button.callback = self.on_return
        self.build()

    def build(self):
        self.clear_items()
        if self.target is None:
            line = f"**{self.source.display_name}** {self.verb}"
            footer = ""
        elif self.target.id == self.source.id:
            line = f"**{self.source.display_name}** {self.verb} **themselves**"
            footer = ""
        else:
            line = f"**{self.source.display_name}** {self.verb} **{self.target.display_name}**"
            footer = f"\n- **Total:** {self.count} time{'s' if self.count != 1 else ''} from {self.source.display_name} to {self.target.display_name}"
        children = []
        if self.gif:
            children.append(ui.gallery(self.gif))
        children.append(ui.text(line))
        if footer:
            children += [ui.sep(), ui.text(footer.strip())]
        if self.button is not None:
            children += [ui.sep(), ui.row(self.button)]
        self.add_item(ui.card(*children))

    async def interaction_check(self, interaction):
        if self.target is not None and interaction.user.id == self.target.id:
            return True
        await interaction.response.send_message(
            view=ui.Notice("err", f"Only **{self.target.display_name}** can use this button."), ephemeral=True
        )
        return False

    async def on_return(self, interaction):
        count = await self.cog.bot.db.bump_interaction(self.target.id, self.source.id, self.action)
        gif = self.cog.bot.gifs.get(self.action)
        reply = RoleplayView(self.cog, self.action, ALL_ACTIONS[self.action], gif, self.target, self.source, count, False)
        self.button.disabled = True
        self.build()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(view=reply)


class Fun(MalfoyCog):
    category = "Fun"

    def __init__(self, bot):
        super().__init__(bot)
        self.dynamic = []
        self.last_used = {}

    async def cog_load(self):
        for action, verb in ALL_ACTIONS.items():
            targeted = action in TARGETED
            if not self.bot.gifs.has(action) or self.bot.get_command(action) is not None:
                continue
            cmd = commands.Command(
                self.make_callback(action, verb, targeted),
                name=action,
                help=f"{'Target someone and ' if targeted else ''}{action} with an anime gif.",
                extras={"owner": "Fun", "category": "Fun"},
            )
            self.bot.add_command(cmd)
            self.dynamic.append(cmd.name)

    async def cog_unload(self):
        for name in self.dynamic:
            self.bot.remove_command(name)
        self.dynamic.clear()

    def make_callback(self, action, verb, targeted):
        async def callback(ctx, user: Optional[discord.User] = None):
            await self.perform(ctx, action, verb, targeted, user)

        callback.__name__ = f"rp_{action}"
        return callback

    async def perform(self, ctx, action, verb, targeted, user):
        now = time.time()
        if now - self.last_used.get(ctx.author.id, 0) < 2.5:
            return await ui.notice(ctx, "warn", "Slow down a little.")
        if targeted and user is None:
            return await ui.notice(ctx, "err", f"Mention someone to {action}!")
        self.last_used[ctx.author.id] = now
        gif = self.bot.gifs.get(action)
        target = user if targeted else None
        count = 0
        can_return = False
        if target is not None:
            count = await self.bot.db.bump_interaction(ctx.author.id, target.id, action)
            can_return = not target.bot and target.id != ctx.author.id
        view = RoleplayView(self, action, verb, gif, ctx.author, target, count, can_return)
        view.message = await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="roleplay", aliases=["rp", "action"], help="Use any roleplay action with an optional target.")
    async def roleplay(self, ctx, action: str, user: Optional[discord.User] = None):
        key = action.lower()
        if key not in ALL_ACTIONS or not self.bot.gifs.has(key):
            return await ui.notice(ctx, "err", "I don't know that action. Try `help fun` to see them all.")
        await self.perform(ctx, key, ALL_ACTIONS[key], key in TARGETED, user)

    @roleplay.autocomplete("action")
    async def roleplay_autocomplete(self, interaction, current):
        names = sorted(n for n in ALL_ACTIONS if current.lower() in n)
        return [app_commands.Choice(name=n, value=n) for n in names[:25]]

    @commands.hybrid_command(name="8ball", aliases=["8b", "ask"], help="Ask the magic 8ball a question.")
    async def eightball(self, ctx, *, question: str):
        answer = random.choice(data.EIGHT_BALL)
        view = ui.Static(ui.head(E.STAR, "Magic 8ball"), ui.sep(), ui.text(ui.bullets([("Question", question[:300]), ("Answer", answer)])))
        await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="ship", help="Check the love meter between two people.")
    async def ship(self, ctx, first: discord.User, second: Optional[discord.User] = None):
        other = second or ctx.author
        pair = sorted([first.id, other.id])
        digest = hashlib.sha256(f"{pair[0]}:{pair[1]}".encode()).digest()
        percent = digest[0] * 101 // 256
        if percent >= 85:
            verdict = "A perfect match!"
        elif percent >= 60:
            verdict = "There is real chemistry here."
        elif percent >= 35:
            verdict = "Friendship has potential."
        else:
            verdict = "Maybe just stay good friends."
        meter = bar(percent, 100, 12)
        rows = [("Pair", f"{first.display_name} and {other.display_name}"), ("Match", f"{meter} **{percent}%**")]
        view = ui.Static(ui.head(E.HEART, "Love Meter"), ui.sep(), ui.text(ui.bullets(rows)), ui.sep(), ui.text(verdict))
        await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="rate", help="Let me rate anything out of ten.")
    async def rate(self, ctx, *, thing: str):
        digest = hashlib.sha256(thing.lower().strip().encode()).digest()
        score = digest[0] % 11
        rows = [("Subject", thing[:200]), ("Score", f"{score}/10 {bar(score, 10)}")]
        await ctx.reply(view=ui.Static(ui.head(E.STAR, "Rating"), ui.sep(), ui.text(ui.bullets(rows))), mention_author=False)

    @commands.hybrid_command(name="choose", aliases=["pick"], help="Pick one option. Separate them with | or commas.")
    async def choose(self, ctx, *, options: str):
        parts = [p.strip() for p in (options.split("|") if "|" in options else options.split(",")) if p.strip()]
        if len(parts) < 2:
            return await ui.notice(ctx, "err", "Give me at least two options separated by `|` or commas.")
        await ui.notice(ctx, "info", f"{E.STAR} I choose **{random.choice(parts)[:200]}**")

    def help_sections(self, prefix):
        targeted = " ".join(f"`{a}`" for a in sorted(TARGETED) if a in self.dynamic)
        solo = " ".join(f"`{a}`" for a in sorted(SOLO) if a in self.dynamic)
        sections = []
        if targeted:
            sections.append(("Actions", targeted))
        if solo:
            sections.append(("Reactions", solo))
        sections.append(("Extras", "`roleplay` `8ball` `ship` `rate` `choose`"))
        return sections


async def setup(bot):
    await bot.add_cog(Fun(bot))
