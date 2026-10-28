from typing import Optional

import discord
from discord import ui as dui
from discord.ext import commands

import config
from core import ui
from core.base import MalfoyCog
from core.emojis import E

class HelpView(ui.Layout):
    def __init__(self, cog, ctx, banner):
        super().__init__(author=ctx.author, timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.banner = banner
        self.index = -1
        self.ordered, self.present = self.collect()
        self.build()

    def collect(self):
        present = {}
        for cog in self.cog.bot.cogs.values():
            category = getattr(cog, "category", None)
            if category and cog.visible_commands():
                present.setdefault(category, cog)
        ordered = [c for c in config.HELP_CATEGORIES if c in present]
        ordered += [c for c in present if c not in ordered]
        return ordered, present

    def icon(self, name):
        return E(config.CATEGORY_ICONS.get(name, "ARROW"))

    def build(self):
        self.clear_items()
        prefix = self.cog.bot.prefix_for(self.ctx.guild)
        children = []
        if self.banner:
            children.append(ui.gallery(self.banner))
        if self.index < 0:
            total = len({c.qualified_name for c in self.cog.bot.commands if not c.hidden})
            menu = "\n".join(f"- {self.icon(c)} **{c}**".replace("-  ", "- ") for c in self.ordered)
            children += [
                ui.head(E.LOGO, "Help Menu"),
                ui.text("Select a category below to see commands."),
                ui.sep(),
                ui.text(menu),
                ui.sep(),
                ui.text(f"__**Quick Info**__\n- **Prefix:** `{prefix}`\n- **Commands:** {total}\n- **Details:** `{prefix}help <command>`"),
            ]
        else:
            name = self.ordered[self.index]
            children += [ui.head(self.icon(name), name), ui.sep()]
            sections = self.present[name].help_sections(prefix)
            for position, (title, chips) in enumerate(sections):
                children.append(ui.text(ui.block(title, chips)))
                if position < len(sections) - 1:
                    children.append(ui.sep())
        children.append(ui.sep())
        options = [
            discord.SelectOption(
                label=name,
                value=str(i),
                emoji=ui.emoji_or_none(config.CATEGORY_ICONS.get(name, "ARROW")),
                default=i == self.index,
            )
            for i, name in enumerate(self.ordered)
        ]
        select = dui.Select(placeholder="Select Category", options=options)
        select.callback = self.on_select
        children.append(ui.row(select))
        if self.index < 0:
            links = ui.link_buttons(invite=self.cog.bot.invite_url)
            if links:
                children.append(ui.row(*links))
        else:
            prev = dui.Button(style=discord.ButtonStyle.secondary, emoji=ui.emoji_or_none("ARROW_LEFT"), label=None if E("ARROW_LEFT") else "Prev")
            home = dui.Button(style=discord.ButtonStyle.primary, label="Home")
            nxt = dui.Button(style=discord.ButtonStyle.secondary, emoji=ui.emoji_or_none("ARROW"), label=None if E("ARROW") else "Next")
            prev.callback = self.on_prev
            home.callback = self.on_home
            nxt.callback = self.on_next
            children.append(ui.row(prev, home, nxt))
        self.add_item(ui.card(*children))

    async def show(self, interaction, index):
        self.index = index
        self.build()
        await interaction.response.edit_message(view=self)

    async def on_select(self, interaction):
        await self.show(interaction, int(interaction.data["values"][0]))

    async def on_prev(self, interaction):
        await self.show(interaction, (self.index - 1) % len(self.ordered))

    async def on_next(self, interaction):
        await self.show(interaction, (self.index + 1) % len(self.ordered))

    async def on_home(self, interaction):
        await self.show(interaction, -1)


class Help(MalfoyCog):
    category = None

    @commands.hybrid_command(name="help", aliases=["h", "commands"], help="Open the help menu.")
    async def help(self, ctx, *, query: Optional[str] = None):
        if query:
            cmd = self.bot.get_command(query.lower())
            if cmd is not None and not cmd.hidden:
                return await self.command_detail(ctx, cmd)
        banner, files = ui.banner_assets()
        view = HelpView(self, ctx, banner)
        view.message = await ctx.reply(view=view, files=files, mention_author=False)

    async def command_detail(self, ctx, cmd):
        prefix = self.bot.prefix_for(ctx.guild)
        category = getattr(cmd.cog, "category", None) or cmd.extras.get("category") or "General"
        rows = [
            ("Usage", f"`{prefix}{cmd.qualified_name} {cmd.signature}`".replace(" `", "`")),
            ("Aliases", ", ".join(f"`{a}`" for a in cmd.aliases) or "None"),
            ("Category", category),
        ]
        if isinstance(cmd, commands.Group):
            rows.append(("Subcommands", ", ".join(f"`{s.name}`" for s in cmd.commands if not s.hidden)))
        view = ui.Static(
            ui.head(E.LOGO, cmd.qualified_name),
            ui.text(cmd.help or "No description yet."),
            ui.sep(),
            ui.text(ui.bullets(rows)),
        )
        await ctx.reply(view=view, mention_author=False)


async def setup(bot):
    await bot.add_cog(Help(bot))
