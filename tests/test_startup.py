import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import AsyncMock, patch

import config
from core.bot import Malfoy


class StartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_syncs_emojis_and_loads_commands(self):
        await self.check_startup()

    async def test_emoji_sync_failure_does_not_stop_startup(self):
        await self.check_startup(RuntimeError("Discord is unavailable"))

    async def check_startup(self, sync_error=None):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            config, "DATABASE_PATH", str(Path(directory) / "bot.db")
        ):
            async with Malfoy() as bot:
                with patch.object(bot.gifs, "load", new_callable=AsyncMock), patch.object(
                    bot.tree, "sync", new_callable=AsyncMock, return_value=[]
                ) as slash_sync, patch.object(
                    bot, "fetch_application_emojis", new_callable=AsyncMock
                ) as fetch_emojis, patch.object(
                    bot, "create_application_emoji", new_callable=AsyncMock
                ) as create_emoji, patch(
                    "core.emojis.UPLOADED", Path(directory) / "emojis_uploaded.json"
                ), patch("core.emojis.E._data", {}), patch(
                    "core.bot.sync_emojis", new_callable=AsyncMock, side_effect=sync_error
                ) as emoji_sync:
                    with self.assertLogs("malfoy", level="ERROR") if sync_error else nullcontext() as logs:
                        await bot.setup_hook()
                    if sync_error:
                        self.assertIn("Emoji sync failed", logs.output[0])

                    self.assertEqual(set(bot.extensions), set(config.EXTENSIONS))
                    self.assertIsNotNone(await bot.db.fetchone("SELECT 1"))
                    slash_sync.assert_awaited_once()
                    emoji_sync.assert_awaited_once_with(bot)
                    fetch_emojis.assert_not_awaited()
                    create_emoji.assert_not_awaited()
                    self.assertFalse((Path(directory) / "emojis_uploaded.json").exists())
                    manual_sync = bot.get_command("emojisync")
                    self.assertIsNotNone(manual_sync)
                    self.assertTrue(manual_sync.hidden)

                    # The explicit owner command still runs its uploader.
                    with patch("cogs.owner.sync_emojis", new_callable=AsyncMock, return_value={}) as upload, patch(
                        "cogs.owner.ui.notice", new_callable=AsyncMock
                    ):
                        await manual_sync.callback(manual_sync.cog, object())
                        upload.assert_awaited_once_with(bot)


if __name__ == "__main__":
    unittest.main()
