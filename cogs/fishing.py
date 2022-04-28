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

    @app_commands.command(name="cast", description="Cast your line out into the realm of fishies")
    async def _cast(self, interaction: discord.Interaction):
        ...

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user = await self.bot.d.fetchone("SELECT * FROM users WHERE id=?;", interaction.user.id)
        if user is None:
            await interaction.response.send_message("You are not registered in my database, let me remedy that for you...")
            await self.bot.d.execute("INSERT INTO users (id) VALUES (?);", interaction.user.id)
            return False
        return True

async def setup(bot: YoFishing):
    bot.tree.add_command(Fishing(bot))
