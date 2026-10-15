import discord
from discord.ext import commands

import config
from core import ui
from core.base import LuniiCog
from core.emojis import sync_emojis
from core.utils import fmt


class Owner(LuniiCog):
    category = None

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(name="reload", hidden=True)
    async def reload(self, ctx, name: str = None):
        targets = [f"cogs.{name}"] if name else list(config.EXTENSIONS)
        done = []
        for extension in targets:
            try:
                await self.bot.reload_extension(extension)
                done.append(extension.split(".")[-1])
            except Exception as exc:
                return await ui.notice(ctx, "err", f"Failed on `{extension}`: {exc}")
        await ui.notice(ctx, "ok", f"Reloaded {', '.join(done)}")

    @commands.command(name="sync", hidden=True)
    async def sync(self, ctx):
        synced = await self.bot.tree.sync()
        await ui.notice(ctx, "ok", f"Synced **{len(synced)}** slash commands.")

    @commands.command(name="emojisync", hidden=True)
    async def emojisync(self, ctx):
        result = await sync_emojis(self.bot)
        await ui.notice(ctx, "ok", f"Emoji sync finished with **{len(result)}** emojis ready.")

    @commands.command(name="addcoins", hidden=True)
    async def addcoins(self, ctx, user: discord.User, amount: int):
        total = await self.bot.db.add_cash(user.id, amount)
        await ui.notice(ctx, "ok", f"{user.display_name} now has **{fmt(total)}** {config.CURRENCY}.")

    @commands.command(name="setcoins", hidden=True)
    async def setcoins(self, ctx, user: discord.User, amount: int):
        await self.bot.db.set_cash(user.id, amount)
        await ui.notice(ctx, "ok", f"Set {user.display_name} to **{fmt(max(0, amount))}** {config.CURRENCY}.")

    @commands.group(name="blacklist", hidden=True, invoke_without_command=True)
    async def blacklist(self, ctx):
        await ui.notice(ctx, "info", f"{len(self.bot.blacklisted)} users are blacklisted. Use `blacklist add` or `blacklist remove`.")

    @blacklist.command(name="add", hidden=True)
    async def blacklist_add(self, ctx, user: discord.User, *, reason: str = ""):
        await self.bot.db.add_blacklist(user.id, reason)
        self.bot.blacklisted.add(user.id)
        await ui.notice(ctx, "ok", f"Blacklisted {user.display_name}.")

    @blacklist.command(name="remove", hidden=True)
    async def blacklist_remove(self, ctx, user: discord.User):
        await self.bot.db.remove_blacklist(user.id)
        self.bot.blacklisted.discard(user.id)
        await ui.notice(ctx, "ok", f"Removed {user.display_name} from the blacklist.")

    @commands.command(name="shutdown", hidden=True)
    async def shutdown(self, ctx):
        await ui.notice(ctx, "info", "Shutting down.")
        await self.bot.close()


async def setup(bot):
    await bot.add_cog(Owner(bot))
