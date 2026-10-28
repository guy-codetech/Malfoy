import json
import logging
import random
from pathlib import Path

import config

log = logging.getLogger("malfoy.gifs")

SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "gif_index.json"


class GifPool:
    def __init__(self):
        self.sources = {}

    def _load_snapshot(self):
        try:
            return json.loads(SNAPSHOT.read_text())
        except (OSError, ValueError):
            return {}

    async def load(self, session):
        snapshot = self._load_snapshot()
        for source in config.GIF_SOURCES:
            name = source["name"]
            categories = None
            try:
                async with session.get(source["index"], timeout=10) as resp:
                    if resp.status == 200:
                        data = json.loads(await resp.text())
                        categories = data.get("categories")
            except Exception as exc:
                log.warning("Could not fetch gif index for %s: %s", name, exc)
            if not categories:
                categories = snapshot.get(name, {})
            self.sources[name] = {"base": source["base"], "categories": categories}
        total = sum(sum(s["categories"].values()) for s in self.sources.values())
        log.info("Gif pool ready with %d gifs", total)

    def categories(self):
        names = set()
        for source in self.sources.values():
            names.update(source["categories"].keys())
        return names

    def has(self, category):
        return category in self.categories()

    def get(self, category):
        options = []
        for source in self.sources.values():
            count = source["categories"].get(category, 0)
            if count:
                options.append((source["base"], count))
        if not options:
            return None
        base, count = random.choices(options, weights=[c for _, c in options])[0]
        return f"{base}/{category}/{random.randint(1, count)}.gif"
