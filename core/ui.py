import inspect
from pathlib import Path

import discord
from discord import ui

import config
from core.emojis import E

ASSETS = Path(__file__).resolve().parent.parent / "assets"

KINDS = {
    "ok": ("TICK", config.ACCENT_OK),
    "err": ("DENIED", config.ACCENT_ERR),
    "warn": ("WARN", config.ACCENT_WARN),
    "info": ("INFO", config.ACCENT_INFO),
}


def text(content):
    return ui.TextDisplay(content)


def sep(visible=True, large=False):
    spacing = discord.SeparatorSpacing.large if large else discord.SeparatorSpacing.small
    return ui.Separator(visible=visible, spacing=spacing)


def section(content, url):
    return ui.Section(ui.TextDisplay(content), accessory=ui.Thumbnail(url))


def gallery(*urls):
    items = [discord.MediaGalleryItem(url) for url in urls]
    params = list(inspect.signature(ui.MediaGallery.__init__).parameters.values())[1:]
    if params and params[0].kind is inspect.Parameter.VAR_POSITIONAL:
        return ui.MediaGallery(*items)
    return ui.MediaGallery(items)


def card(*children, accent=None):
    colour = discord.Colour(config.ACCENT if accent is None else accent)
    return ui.Container(*children, accent_colour=colour)


def row(*items):
    return ui.ActionRow(*items)


def link_buttons(invite=None, support=None, website=None):
    buttons = []
    if invite:
        buttons.append(ui.Button(style=discord.ButtonStyle.link, label="Invite", url=invite))
    if support or config.SUPPORT_URL:
        buttons.append(ui.Button(style=discord.ButtonStyle.link, label="Support", url=support or config.SUPPORT_URL))
    if website or config.WEBSITE_URL:
        buttons.append(ui.Button(style=discord.ButtonStyle.link, label="Website", url=website or config.WEBSITE_URL))
    return buttons


def emoji_or_none(key):
    value = E(key)
    return value or None


def banner_assets():
    if config.BANNER_URL:
        return config.BANNER_URL, []
    path = ASSETS / "banner.png"
    if not path.exists():
        return None, []
    return "attachment://banner.png", [discord.File(path, filename="banner.png")]


class Layout(ui.LayoutView):
    def __init__(self, *, author=None, timeout=120):
        super().__init__(timeout=timeout)
        self.author = author
        self.message = None

    async def interaction_check(self, interaction):
        if self.author is not None and interaction.user.id != self.author.id:
            await interaction.response.send_message(
                view=Notice("err", "This panel belongs to someone else. Run the command yourself to get one."),
                ephemeral=True,
            )
            return False
        return True

    def disable_all(self):
        for item in self.walk_children():
            if hasattr(item, "disabled") and getattr(item, "url", None) is None:
                item.disabled = True

    async def on_timeout(self):
        self.disable_all()
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Notice(ui.LayoutView):
    def __init__(self, kind, message):
        super().__init__(timeout=None)
        icon, colour = KINDS[kind]
        prefix = f"{E(icon)} " if E(icon) else ""
        self.add_item(card(text(f"{prefix}{message}"), accent=colour))


async def notice(ctx, kind, message, **kwargs):
    return await ctx.reply(view=Notice(kind, message), mention_author=False, **kwargs)



class Static(ui.LayoutView):
    def __init__(self, *children, accent=None):
        super().__init__(timeout=None)
        self.add_item(card(*children, accent=accent))


def head(icon, title):
    return text(f"### {icon} {title}".replace("###  ", "### "))


def bullets(rows):
    out = []
    for row in rows:
        label, value = row[0], row[1]
        icon = E(row[2]) if len(row) > 2 else ""
        out.append(f"- {icon} **{label}:** {value}".replace("-  ", "- "))
    return "\n".join(out)


def block(title, body):
    return f"__**{title}**__\n{body}"


def image_file(data, name="card.png"):
    import io

    return discord.File(io.BytesIO(data), filename=name)


class PageView(Layout):
    def __init__(self, ctx, pages, *, links=None, start=0, timeout=180):
        super().__init__(author=ctx.author, timeout=timeout)
        self.pages = pages
        self.index = start
        self.links = links or []
        self.build()

    def build(self):
        self.clear_items()
        children = list(self.pages[self.index]())
        children.append(sep())
        prev = ui.Button(style=discord.ButtonStyle.secondary, emoji=emoji_or_none("ARROW_LEFT"), label=None if E("ARROW_LEFT") else "Prev")
        home = ui.Button(style=discord.ButtonStyle.primary, label=f"Home  {self.index + 1}/{len(self.pages)}")
        nxt = ui.Button(style=discord.ButtonStyle.secondary, emoji=emoji_or_none("ARROW"), label=None if E("ARROW") else "Next")
        prev.callback = self.on_prev
        home.callback = self.on_home
        nxt.callback = self.on_next
        children.append(row(prev, home, nxt, *self.links[:2]))
        self.add_item(card(*children))

    async def go(self, interaction, index):
        self.index = index % len(self.pages)
        self.build()
        await interaction.response.edit_message(view=self)

    async def on_prev(self, interaction):
        await self.go(interaction, self.index - 1)

    async def on_next(self, interaction):
        await self.go(interaction, self.index + 1)

    async def on_home(self, interaction):
        await self.go(interaction, 0)
