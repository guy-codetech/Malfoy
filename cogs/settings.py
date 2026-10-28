from typing import Optional

import discord
from discord.ext import commands

import config
from core import ui
from core.base import MalfoyCog
from core.emojis import E


class Settings(MalfoyCog):
    category = "Settings"
    groups = [("Server", ["settings", "prefix", "channel"])]

    def channels_text(self, guild):
        ids = sorted(self.bot.gates.get(guild.id, set()))
        return ", ".join(f"<#{i}>" for i in ids) if ids else "Every channel"

    @commands.hybrid_command(name="settings", aliases=["config"], help="View this server's settings.")
    @commands.guild_only()
    async def settings(self, ctx):
        prefix = self.bot.prefix_for(ctx.guild)
        rows = [("Prefix", f"`{prefix}`", "ARROW"), ("Game channels", self.channels_text(ctx.guild), "ARROW")]
        tips = f"__**Manage**__\n- `{prefix}prefix <new>` changes the prefix\n- `{prefix}channel add` limits game commands to a channel"
        view = ui.Static(ui.head(E.SETTINGS, "Server Settings"), ui.sep(), ui.text(ui.bullets(rows)), ui.sep(), ui.text(tips))
        await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="prefix", help="Show or change the prefix for this server.")
    @commands.guild_only()
    async def prefix(self, ctx, new: Optional[str] = None):
        current = self.bot.prefix_for(ctx.guild)
        if new is None:
            return await ui.notice(ctx, "info", f"My prefix here is `{current}`. You can also mention me.")
        if not ctx.author.guild_permissions.manage_guild:
            return await ui.notice(ctx, "err", "You need **Manage Server** to change the prefix.")
        if len(new) > 5 or any(ch.isspace() or ch in "`<>@#" for ch in new):
            return await ui.notice(ctx, "err", "Prefixes can be up to 5 characters with no spaces, backticks or mentions.")
        await self.bot.db.set_prefix(ctx.guild.id, new)
        self.bot.prefixes[ctx.guild.id] = new
        await ui.notice(ctx, "ok", f"Prefix updated to `{new}`")

    @commands.hybrid_group(
        name="channel",
        aliases=["channels"],
        fallback="list",
        help="Limit game and economy commands to specific channels.",
    )
    @commands.guild_only()
    async def channel(self, ctx):
        view = ui.Static(
            ui.head(E.SETTINGS, "Game Channels"),
            ui.sep(),
            ui.text(f"- **Allowed:** {self.channels_text(ctx.guild)}"),
            ui.sep(),
            ui.text("Economy, bank, games and fun commands only run in these channels when any are set."),
        )
        await ctx.reply(view=view, mention_author=False)

    @channel.command(name="add", help="Allow game commands in a channel.")
    @commands.has_permissions(manage_guild=True)
    async def channel_add(self, ctx, channel: Optional[discord.TextChannel] = None):
        target = channel or ctx.channel
        ids = set(self.bot.gates.get(ctx.guild.id, set()))
        ids.add(target.id)
        self.bot.gates[ctx.guild.id] = ids
        await self.bot.db.set_channels(ctx.guild.id, ids)
        await ui.notice(ctx, "ok", f"Game commands are now allowed in {target.mention}.")

    @channel.command(name="remove", help="Stop allowing game commands in a channel.")
    @commands.has_permissions(manage_guild=True)
    async def channel_remove(self, ctx, channel: Optional[discord.TextChannel] = None):
        target = channel or ctx.channel
        ids = set(self.bot.gates.get(ctx.guild.id, set()))
        ids.discard(target.id)
        if ids:
            self.bot.gates[ctx.guild.id] = ids
        else:
            self.bot.gates.pop(ctx.guild.id, None)
        await self.bot.db.set_channels(ctx.guild.id, ids)
        await ui.notice(ctx, "ok", f"Removed {target.mention} from the allowed channels.")

    @channel.command(name="clear", help="Allow game commands everywhere again.")
    @commands.has_permissions(manage_guild=True)
    async def channel_clear(self, ctx):
        self.bot.gates.pop(ctx.guild.id, None)
        await self.bot.db.set_channels(ctx.guild.id, set())
        await ui.notice(ctx, "ok", "Game commands now work in every channel.")


async def setup(bot):
    await bot.add_cog(Settings(bot))
