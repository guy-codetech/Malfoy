import logging
import sys

import config
from core.bot import Malfoy


def main():
    if not config.TOKEN:
        print("No TOKEN found. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    bot = Malfoy()
    bot.run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
