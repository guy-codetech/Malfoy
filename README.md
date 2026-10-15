<p align="center">
  <img src="assets/banner.png" alt="Lunii" width="100%">
</p>

<h1 align="center">Lunii</h1>

<p align="center">A little world of coins and chaos. Cute economy, games and roleplay Discord bot built with Python and discord.py.</p>

---

## Features

<table>
<tr>
<td width="33%" valign="top">

**Economy**

- Wallet, bank and bank upgrades
- Daily rewards with streaks
- Work, beg, crime and rob
- Hunt and fish, zoo collection
- Shop, inventory and lootboxes
- Profile and rank cards
- Leaderboards

</td>
<td width="33%" valign="top">

**Games & Fun**

- Coinflip, slots, blackjack
- Roulette, dice and rock paper scissors
- 50+ roleplay actions with GIFs
- Ship, rate, 8ball and choose

</td>
<td width="33%" valign="top">

**Utility**

- User, server and role info
- Avatar, banner and server icon
- Calculator and reminders
- Per-server prefix
- Channel limits for game commands
- Slash and prefix commands

</td>
</tr>
</table>

## Setup

<table>
<tr>
<td><b>1. Clone</b></td>
<td>

```bash
git clone https://github.com/r3novadcl/lunii.git
cd lunii
```

</td>
</tr>
<tr>
<td><b>2. Install</b></td>
<td>

```bash
pip install -r requirements.txt
```

</td>
</tr>
<tr>
<td><b>3. Configure</b></td>
<td>

Copy `.env.example` to `.env` and fill it in:

```env
TOKEN=YOUR_BOT_TOKEN
OWNER_IDS=YOUR_DISCORD_ID
PREFIX=l
```

Turn on the **Message Content** intent in the Developer Portal.

</td>
</tr>
<tr>
<td><b>4. Run</b></td>
<td>

```bash
python main.py
```

Custom emojis upload automatically on the first start.

</td>
</tr>
<tr>
<td><b>5. Profile</b> <sub>(optional)</sub></td>
<td>

```bash
python script/set_profile.py
```

Sets the bot avatar and banner.

</td>
</tr>
</table>

## Configuration

<table>
<tr>
<td><b>.env</b></td>
<td>Token, owner IDs, prefix, support and website links, log channel</td>
</tr>
<tr>
<td><b>config.py</b></td>
<td>Name, accent colours, rewards, cooldowns, bet limits, GIF sources</td>
</tr>
</table>

## Owner Commands

`reload`, `sync`, `emojisync`, `addcoins`, `setcoins`, `blacklist`, `shutdown`

## Requirements

<table>
<tr>
<td><b>Python</b></td>
<td>3.10+</td>
</tr>
<tr>
<td><b>discord.py</b></td>
<td>2.6+</td>
</tr>
<tr>
<td><b>Discord Bot</b></td>
<td>Token + Message Content intent</td>
</tr>
</table>

## Credits

Roleplay GIFs are loaded from the community repositories
[bre4d777/anime-gifs](https://github.com/bre4d777/anime-gifs) and
[itsfizys/roleplay-gifs](https://github.com/itsfizys/roleplay-gifs).

## License

Free for personal, educational and non-profit use. Selling it, or using it to make money, is not allowed. See [LICENSE](LICENSE).

Want an official version, commercial use or a custom bot? Contact FX Development:
[discord.gg/epKhYP6Y74](https://discord.gg/epKhYP6Y74)

---

<table align="center">
<tr>
<td align="center" width="500">FX Development

<br>Developed by

<a href="https://discord.com/users/1484508031923392522">
  <b>r3novadcl</b>
</a><br><sub>Discord ID: 1484508031923392522</sub>

</td>
</tr>
</table>

<p align="center">
  <sub>© FX Development · Lunii</sub>
</p>
