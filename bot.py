import os

import asqlite
import discord
from discord import app_commands
from discord.ext import commands


class Tree(app_commands.CommandTree):
    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if not interaction.response.is_done():
            method = interaction.response.send_message
        else:
            method = interaction.followup.send

        if isinstance(error, app_commands.errors.CommandOnCooldown):
            await method(
                f"Slow down! You can use this command again in {error.retry_after:.2f} seconds",
                ephemeral=True,
            )


class YoFishing(commands.Bot):
    def __init__(self, d: asqlite.Connection, sync: bool):
        self.sync_on_startup = sync
        self.d = d

        super().__init__(
            command_prefix=commands.when_mentioned,
            help_commands=None,
            max_messages=None,
            intents=discord.Intents(guilds=True),
            chunk_guilds_at_startup=False,
            allowed_mentions=discord.AllowedMentions(
                everyone=False, roles=False, users=False
            ),
            tree_cls=Tree,
            owner_id=737928480389333004,
        )

    async def setup_hook(self):
        for file in os.listdir("cogs"):
            if file.endswith(".py") and not file.startswith("_"):
                await self.load_extension("cogs." + file[:-3])

        if self.sync_on_startup:

            async def sync_task():
                await self.wait_until_ready()
                await self.tree.sync()

            self.loop.create_task(sync_task())

    async def on_ready(self):
        print("Bot is ready!")
