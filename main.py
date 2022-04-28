import argparse
import asyncio

import asqlite

import config
from bot import YoFishing

parser = argparse.ArgumentParser()
parser.add_argument("--sync", action="store_true")
args = parser.parse_args()


async def main():
    async with asqlite.connect("data.sqlite") as d:
        bot = YoFishing(d=d, sync=args.sync)
        await bot.start(config.token)


asyncio.run(main())
