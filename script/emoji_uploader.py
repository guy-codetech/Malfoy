import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import discord

import config
from core.emojis import sync_emojis


async def main():
    if not config.TOKEN:
        print("No TOKEN found in .env")
        return
    client = discord.Client(intents=discord.Intents.none())
    async with client:
        await client.login(config.TOKEN)
        result = await sync_emojis(client)
        print(f"Done. {len(result)} emojis are ready and saved to emojis_uploaded.json")


if __name__ == "__main__":
    asyncio.run(main())
