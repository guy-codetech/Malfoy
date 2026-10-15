import asyncio
import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import discord
from discord.http import Route

import config


def data_uri(path):
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/png;base64,{encoded}"


async def main():
    if not config.TOKEN:
        print("No TOKEN found in .env")
        return
    payload = {}
    avatar = ROOT / "assets" / "avatar.png"
    banner = ROOT / "assets" / "banner.png"
    if avatar.exists():
        payload["avatar"] = data_uri(avatar)
    if banner.exists():
        payload["banner"] = data_uri(banner)
    client = discord.Client(intents=discord.Intents.none())
    async with client:
        await client.login(config.TOKEN)
        await client.http.request(Route("PATCH", "/users/@me"), json=payload)
        print("Avatar and banner updated.")


if __name__ == "__main__":
    asyncio.run(main())
