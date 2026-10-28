import asyncio
import hashlib
import json
import logging
from pathlib import Path

import discord

import config

log = logging.getLogger("malfoy.emojis")

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "emojis.json"
UPLOADED = ROOT / "emojis_uploaded.json"
EMOJI_DIR = ROOT / "assets" / "emojis"
BRANDED_KEYS = {"LOGO", "COIN"}


class EmojiMap:
    def __init__(self):
        self._data = {}
        self.load()

    def load(self):
        try:
            self._data = json.loads(UPLOADED.read_text())
        except (OSError, ValueError):
            self._data = {}

    def get(self, key, default=""):
        return self._data.get(str(key).upper(), default)

    def __call__(self, key, default=""):
        return self.get(key, default)

    def __getitem__(self, key):
        return self.get(key)

    def __contains__(self, key):
        return str(key).upper() in self._data

    def __getattr__(self, key):
        if key.startswith("_"):
            raise AttributeError(key)
        return self.get(key)

    def keys(self):
        return list(self._data.keys())


E = EmojiMap()


def needs_sync():
    try:
        manifest = json.loads(MANIFEST.read_text())
    except (OSError, ValueError):
        return False
    return any(key not in E for key in manifest)


async def sync_emojis(client):
    manifest = json.loads(MANIFEST.read_text())
    existing = {emoji.name: emoji for emoji in await client.fetch_application_emojis()}
    result = {}
    for key, filename in manifest.items():
        name = f"{config.EMOJI_PREFIX}{key.lower()}"
        path = EMOJI_DIR / filename
        if key in BRANDED_KEYS:
            if not path.exists():
                log.warning("Missing emoji file %s", path)
                continue
            # Discord cannot replace emoji images in place. Version mascot names
            # by content so manual sync refreshes the cache and reuses each upload.
            name += f"_{hashlib.sha256(path.read_bytes()).hexdigest()[:8]}"
        emoji = existing.get(name)
        if emoji is None:
            if not path.exists():
                log.warning("Missing emoji file %s", path)
                continue
            try:
                emoji = await client.create_application_emoji(name=name, image=path.read_bytes())
            except discord.HTTPException as exc:
                log.warning("Could not synchronize %s: %s", name, exc)
                continue
            await asyncio.sleep(0.6)
        result[key] = str(emoji)
    UPLOADED.write_text(json.dumps(result, indent=2) + "\n")
    E.load()
    log.info("Emoji sync complete: %d emojis ready", len(result))
    return result
