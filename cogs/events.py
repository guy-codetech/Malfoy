import random
import time

import discord
from discord.ext import commands

import config
from core import ui, utils
from core.base import MalfoyCog
from core.bot import category_of
from core.emojis import E


class Events(MalfoyCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.last_xp = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or self.bot.user is None:
            return
        if message.content.strip() not in (f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"):
            return
        if message.author.id in self.bot.blacklisted:
            return
        prefix = self.bot.prefix_for(message.guild)
        rows = [
            ("Prefix", f"`{prefix}`", "ARROW"),
            ("Servers", utils.fmt(len(self.bot.guilds)), "ARROW"),
            ("Uptime", utils.duration(time.time() - self.bot.started_at), "ARROW"),
        ]
        children = [
            ui.head(E.LOGO, f"Hey, I'm {config.BOT_NAME}"),
            ui.text(config.TAGLINE),
            ui.sep(),
            ui.text(ui.bullets(rows)),
            ui.sep(),
            ui.text(f"Type `{prefix}help` to see everything I can do."),
        ]
        buttons = ui.link_buttons(invite=self.bot.invite_url)
        if buttons:
            children += [ui.sep(), ui.row(*buttons)]
        try:
            await message.reply(view=ui.Static(*children), mention_author=False)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        category = category_of(ctx)
        if category not in config.GATED_CATEGORIES:
            return
        now = time.time()
        amount = 0
        if now - self.last_xp.get(ctx.author.id, 0) >= config.XP_COOLDOWN:
            self.last_xp[ctx.author.id] = now
            amount = random.randint(*config.XP_RANGE)
        old, new = await self.bot.db.add_xp(ctx.author.id, amount)
        if new > old:
            reward = config.LEVEL_UP_REWARD * new
            await self.bot.db.add_cash(ctx.author.id, reward)
            try:
                await ui.notice(
                    ctx,
                    "ok",
                    f"**Level up!** {ctx.author.display_name} reached level **{new}** and earned "
                    f"**{utils.fmt(reward)}** {config.CURRENCY} {E.COIN}",
                )
            except discord.HTTPException:
                pass

    async def log_guild(self, guild, joined):
        await self.bot.refresh_presence()
        if not config.LOG_CHANNEL_ID:
            return
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        if channel is None:
            return
        verb = "Joined" if joined else "Left"
        rows = [
            ("Name", guild.name),
            ("ID", f"`{guild.id}`"),
            ("Members", utils.fmt(guild.member_count or 0)),
            ("Total servers", utils.fmt(len(self.bot.guilds))),
        ]
        colour = config.ACCENT_OK if joined else config.ACCENT_ERR
        try:
            await channel.send(view=ui.Static(ui.head(E.LOGO, f"{verb} a server"), ui.sep(), ui.text(ui.bullets(rows)), accent=colour))
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.log_guild(guild, True)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.log_guild(guild, False)


async def setup(bot):
    await bot.add_cog(Events(bot))
