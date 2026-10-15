import time

from discord.ext import commands

from core import ui


class LuniiCog(commands.Cog):
    category = None

    def __init__(self, bot):
        self.bot = bot

    def visible_commands(self):
        found = []
        for cmd in self.bot.commands:
            owned = cmd.cog is self or cmd.extras.get("owner") == type(self).__name__
            if owned and not cmd.hidden:
                found.append(cmd)
        return sorted(found, key=lambda c: c.name)

    groups = None

    def help_sections(self, prefix):
        names = []
        for cmd in self.visible_commands():
            names.append(cmd.qualified_name)
            if isinstance(cmd, commands.Group):
                names += [s.qualified_name for s in sorted(cmd.commands, key=lambda c: c.name) if not s.hidden]
        sections = []
        used = set()
        for title, items in self.groups or []:
            found = [n for n in items if n in names]
            used.update(found)
            if found:
                sections.append((title, " ".join(f"`{n}`" for n in found)))
        rest = [n for n in sorted(names) if n not in used]
        if rest:
            sections.append(("More" if sections else "Commands", " ".join(f"`{n}`" for n in rest)))
        return sections

    async def cooldown(self, ctx, key, seconds=None):
        from core import utils
        import config

        seconds = config.COOLDOWNS[key] if seconds is None else seconds
        left = await self.bot.db.cooldown_left(ctx.author.id, key)
        if left > 0:
            await ui.notice(ctx, "warn", f"Easy there. You can use this again {utils.ts(left)}.")
            return False
        await self.bot.db.set_cooldown(ctx.author.id, key, seconds)
        return True
