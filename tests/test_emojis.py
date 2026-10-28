import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import config
from core import emojis


class EmojiSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_manual_sync_versions_new_mascot_art_and_reuses_uploads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {"LOGO": "logo.png", "COIN": "coin.png", "BANK": "bank.png"}
            manifest_path = root / "emojis.json"
            manifest_path.write_text(json.dumps(manifest))
            for filename in manifest.values():
                (root / filename).write_bytes(filename.encode())
            cache = root / "uploaded.json"
            old = []
            for index, key in enumerate(manifest, 1):
                emoji = MagicMock(name=key)
                emoji.name = f"{config.EMOJI_PREFIX}{key.lower()}"
                emoji.__str__.return_value = f"<:{emoji.name}:{index}>"
                old.append(emoji)
            uploaded = []

            async def create(*, name, image):
                emoji = MagicMock()
                emoji.name = name
                emoji.__str__.return_value = f"<:{name}:{100 + len(uploaded)}>"
                uploaded.append(emoji)
                return emoji

            client = MagicMock()
            client.fetch_application_emojis = AsyncMock(side_effect=lambda: old + uploaded)
            client.create_application_emoji = AsyncMock(side_effect=create)
            with patch.object(emojis, "MANIFEST", manifest_path), patch.object(
                emojis, "EMOJI_DIR", root
            ), patch.object(emojis, "UPLOADED", cache), patch.object(
                emojis.E, "_data", {}
            ), patch("core.emojis.asyncio.sleep", new_callable=AsyncMock):
                result = await emojis.sync_emojis(client)
                self.assertEqual(client.create_application_emoji.await_count, 2)
                for key, new_emoji in zip(("LOGO", "COIN"), uploaded):
                    filename = manifest[key]
                    digest = hashlib.sha256(filename.encode()).hexdigest()[:8]
                    self.assertEqual(new_emoji.name, f"{config.EMOJI_PREFIX}{key.lower()}_{digest}")
                    self.assertEqual(result[key], str(new_emoji))
                    self.assertEqual(emojis.E(key), str(new_emoji))
                self.assertEqual(result["BANK"], str(old[2]))
                self.assertEqual(json.loads(cache.read_text()), result)
                self.assertEqual(await emojis.sync_emojis(client), result)
                self.assertEqual(client.create_application_emoji.await_count, 2)
                for emoji in old:
                    emoji.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
