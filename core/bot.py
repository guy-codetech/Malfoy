import asyncio
import logging
import time
from collections import defaultdict

import aiohttp
import discord
from discord.ext import commands

import config
from core import ui
from core.database import Database
from core.emojis import sync_emojis
from core.gifs import GifPool

log = logging.getLogger("malfoy")


def category_of(ctx):
    category = getattr(ctx.cog, "category", None)
    if category is None and ctx.command is not None:
        category = ctx.command.extras.get("category")
    return category


class ChannelBlocked(commands.CheckFailure):
    pass


class Blacklisted(commands.CheckFailure):
    pass


class Malfoy(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=self.resolve_prefix,
            intents=intents,
            case_insensitive=True,
            strip_after_prefix=True,
            help_command=None,
            allowed_mentions=discord.AllowedMentions.none(),
            owner_ids=set(config.OWNER_IDS),
        )
        self.db = Database(config.DATABASE_PATH)
        self.gifs = GifPool()
        self.session = None
        self.started_at = time.time()
        self.prefixes = {}
        self.gates = {}
        self.blacklisted = set()
        self.active_games = set()
        self.add_check(self.global_check)

    async def resolve_prefix(self, _bot, message):
        prefix = self.prefixes.get(message.guild.id, config.DEFAULT_PREFIX) if message.guild else config.DEFAULT_PREFIX
        choices = [f"<@{self.user.id}> ", f"<@!{self.user.id}> ", prefix]
        if prefix.lower() != prefix.upper():
            choices.append(prefix.upper() if prefix == prefix.lower() else prefix.lower())
        return choices

    def prefix_for(self, guild):
        if guild is None:
            return config.DEFAULT_PREFIX
        return self.prefixes.get(guild.id, config.DEFAULT_PREFIX)

    async def load_guild_cache(self):
        for row in await self.db.guild_settings():
            if row["prefix"]:
                self.prefixes[row["guild_id"]] = row["prefix"]
            ids = {int(x) for x in row["channels"].split(",") if x}
            if ids:
                self.gates[row["guild_id"]] = ids
        self.blacklisted = await self.db.blacklist_ids()

    async def setup_hook(self):
        await self.db.connect()
        await self.load_guild_cache()
        self.session = aiohttp.ClientSession()
        await self.gifs.load(self.session)
        try:
            await sync_emojis(self)
        except Exception:
            log.exception("Emoji sync failed")
        for extension in config.EXTENSIONS:
            try:
                await self.load_extension(extension)
            except Exception:
                log.exception("Failed to load %s", extension)
        if config.SYNC_SLASH_ON_START:
            try:
                synced = await self.tree.sync()
                log.info("Synced %d slash commands", len(synced))
            except Exception:
                log.exception("Slash sync failed")

    async def close(self):
        if self.session is not None:
            await self.session.close()
        await self.db.close()
        await super().close()

    async def on_ready(self):
        log.info("Logged in as %s (%s) in %d servers", self.user, self.user.id, len(self.guilds))
        await self.refresh_presence()

    async def refresh_presence(self):
        text = config.PRESENCE_TEXT.format(prefix=config.DEFAULT_PREFIX, servers=len(self.guilds))
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))

    @property
    def invite_url(self):
        perms = discord.Permissions(
            view_channel=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            add_reactions=True,
            use_external_emojis=True,
            send_messages_in_threads=True,
        )
        return discord.utils.oauth_url(self.user.id, permissions=perms, scopes=("bot", "applications.commands"))

    async def global_check(self, ctx):
        if ctx.author.bot:
            return False
        if ctx.author.id in self.blacklisted:
            raise Blacklisted()
        category = category_of(ctx)
        if ctx.guild and category in config.GATED_CATEGORIES:
            allowed = self.gates.get(ctx.guild.id)
            if allowed and ctx.channel.id not in allowed:
                raise ChannelBlocked()
        return True

    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, "on_error"):
            return
        error = getattr(error, "original", error)
        if isinstance(error, (commands.CommandNotFound, Blacklisted)):
            return
        if isinstance(error, ChannelBlocked):
            allowed = self.gates.get(ctx.guild.id, set())
            where = ", ".join(f"<#{c}>" for c in sorted(allowed)[:5])
            try:
                await ui.notice(ctx, "warn", f"Use this command in {where}.")
            except discord.HTTPException:
                pass
            return
        if isinstance(error, commands.MissingRequiredArgument):
            usage = f"{ctx.clean_prefix}{ctx.command.qualified_name} {ctx.command.signature}".strip()
            return await ui.notice(ctx, "err", f"You are missing `{error.param.name}`.\nUsage: `{usage}`")
        if isinstance(error, (commands.BadArgument, commands.BadUnionArgument, commands.TooManyArguments)):
            message = str(error) or "Those arguments don't look right."
            return await ui.notice(ctx, "err", message)
        if isinstance(error, commands.MissingPermissions):
            need = ", ".join(p.replace("_", " ").title() for p in error.missing_permissions)
            return await ui.notice(ctx, "err", f"You need **{need}** to do that.")
        if isinstance(error, (commands.NotOwner, commands.CheckFailure)):
            return await ui.notice(ctx, "err", "You can't use this command.")
        if isinstance(error, commands.NoPrivateMessage):
            return await ui.notice(ctx, "err", "This command only works in servers.")
        if isinstance(error, commands.CommandOnCooldown):
            return await ui.notice(ctx, "warn", f"Easy there. Try again in {error.retry_after:.0f}s.")
        log.error("Unhandled error in %s", ctx.command, exc_info=error)
        try:
            await ui.notice(ctx, "err", "Something went wrong on my side. Please try again in a moment.")
        except discord.HTTPException:
            pass
