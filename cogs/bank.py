import discord
from discord import ui as dui
from discord.ext import commands

import config
from core import ui, utils
from core.base import MalfoyCog
from core.emojis import E
from core.utils import DepositAmount, WithdrawAmount, fmt


class BankView(ui.Layout):
    def __init__(self, bot, ctx):
        super().__init__(author=ctx.author, timeout=120)
        self.bot = bot
        self.ctx = ctx
        self.status = ""

    async def build(self):
        row = await self.bot.db.user(self.ctx.author.id)
        cost = int(row["bank_cap"] * config.BANK_UPGRADE_COST_RATIO)
        rows = [
            ("Wallet", fmt(row["cash"]), "COIN"),
            ("Stored", f"{fmt(row['bank'])} / {fmt(row['bank_cap'])}", "LOCK"),
            ("Fill", utils.bar(row["bank"], row["bank_cap"], 12), "CHART"),
        ]
        info = [
            ("Interest", f"{config.BANK_INTEREST_RATE * 100:g}% on every daily claim", "STAR"),
            ("Upgrade cost", f"{fmt(cost)} {config.CURRENCY}", "COIN"),
        ]
        deposit = dui.Button(style=discord.ButtonStyle.success, label="Deposit All", emoji=ui.emoji_or_none("BANK"))
        withdraw = dui.Button(style=discord.ButtonStyle.secondary, label="Withdraw All", emoji=ui.emoji_or_none("COIN"))
        upgrade = dui.Button(style=discord.ButtonStyle.primary, label="Upgrade", emoji=ui.emoji_or_none("STAR"))
        deposit.callback = self.on_deposit
        withdraw.callback = self.on_withdraw
        upgrade.callback = self.on_upgrade
        self.clear_items()
        children = [ui.head(E.BANK, f"{self.ctx.author.display_name}'s Vault"), ui.sep(), ui.text(ui.bullets(rows)), ui.sep(), ui.text(ui.bullets(info))]
        if self.status:
            children += [ui.sep(), ui.text(self.status)]
        children += [ui.sep(), ui.row(deposit, withdraw, upgrade)]
        self.add_item(ui.card(*children))

    async def refresh(self, interaction, status):
        self.status = status
        await self.build()
        await interaction.response.edit_message(view=self)

    async def on_deposit(self, interaction):
        row = await self.bot.db.user(self.ctx.author.id)
        amount = min(row["cash"], max(0, row["bank_cap"] - row["bank"]))
        if amount <= 0:
            return await self.refresh(interaction, "Nothing to deposit right now.")
        ok = await self.bot.db.deposit(self.ctx.author.id, amount)
        await self.refresh(interaction, f"{E.TICK} Deposited **{fmt(amount)}**." if ok else "Deposit failed, try again.")

    async def on_withdraw(self, interaction):
        row = await self.bot.db.user(self.ctx.author.id)
        if row["bank"] <= 0:
            return await self.refresh(interaction, "Your vault is empty.")
        ok = await self.bot.db.withdraw(self.ctx.author.id, row["bank"])
        await self.refresh(interaction, f"{E.TICK} Withdrew **{fmt(row['bank'])}**." if ok else "Withdrawal failed, try again.")

    async def on_upgrade(self, interaction):
        ok, cost, cap = await self.bot.db.upgrade_bank(self.ctx.author.id)
        if ok:
            await self.refresh(interaction, f"{E.TICK} Capacity upgraded to **{fmt(cap)}** for {fmt(cost)} {config.CURRENCY}.")
        else:
            await self.refresh(interaction, f"{E.DENIED} You need **{fmt(cost)}** {config.CURRENCY} in your wallet to upgrade.")


class Bank(MalfoyCog):
    category = "Bank"
    groups = [("Vault", ["bank", "deposit", "withdraw", "upgrade"])]

    @commands.hybrid_command(name="bank", aliases=["vault"], help="Open your vault panel.")
    async def bank(self, ctx):
        view = BankView(self.bot, ctx)
        await view.build()
        view.message = await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="deposit", aliases=["dep"], help="Move coins from your wallet into the bank.")
    async def deposit(self, ctx, amount: DepositAmount):
        if not await self.bot.db.deposit(ctx.author.id, amount):
            row = await self.bot.db.user(ctx.author.id)
            room = max(0, row["bank_cap"] - row["bank"])
            return await ui.notice(ctx, "err", f"Your vault only has room for **{fmt(room)}** more. Upgrade it to store more.")
        await ui.notice(ctx, "ok", f"Deposited **{fmt(amount)}** {config.CURRENCY} {E.BANK}")

    @commands.hybrid_command(name="withdraw", aliases=["with"], help="Take coins out of the bank.")
    async def withdraw(self, ctx, amount: WithdrawAmount):
        if not await self.bot.db.withdraw(ctx.author.id, amount):
            return await ui.notice(ctx, "err", "You don't have that much stored in your vault.")
        await ui.notice(ctx, "ok", f"Withdrew **{fmt(amount)}** {config.CURRENCY} {E.COIN}")

    @commands.hybrid_command(name="upgrade", help="Increase your bank capacity.")
    async def upgrade(self, ctx):
        ok, cost, cap = await self.bot.db.upgrade_bank(ctx.author.id)
        if not ok:
            return await ui.notice(ctx, "err", f"An upgrade costs **{fmt(cost)}** {config.CURRENCY} right now.")
        await ui.notice(ctx, "ok", f"Vault capacity is now **{fmt(cap)}** {E.BANK} (cost {fmt(cost)} {config.CURRENCY})")


async def setup(bot):
    await bot.add_cog(Bank(bot))
