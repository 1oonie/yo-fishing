import enum

import discord
from discord import app_commands

from bot import YoFishing


class ItemType(enum.IntEnum):
    fishing_rod = 0
    bait = 1
    fishing_socks = 2
    capitalism_hat = 3
    hammer_and_sickle = 4
    new_new_cheeseland_flag = 5


class ItemRating(enum.IntEnum):
    normal = 0
    unique = 1
    genuine = 2
    strange = 3
    unusual = 4


class Fishing(app_commands.Group, name="fishing"):
    def __init__(self, bot: YoFishing):
        self.bot = bot

        super().__init__()


async def setup(bot: YoFishing):
    bot.tree.add_command(Fishing(bot))
