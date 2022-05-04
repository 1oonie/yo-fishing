import asyncio
import enum
import os
import random
import sqlite3
import time
from typing import Optional, Sequence, cast

import discord
from discord import app_commands, ui

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
    strange = 2
    unusual = 3


class CastView(ui.View):
    message: discord.Message

    def __init__(self, author: discord.abc.User, seconds: int):
        self.author = author
        self.seconds = seconds
        self.start: Optional[float] = None

        asyncio.create_task(self.waiter())

        super().__init__(timeout=30)

    @ui.button(
        label="No bites yet...",
        disabled=True,
        style=discord.ButtonStyle.secondary,
    )
    async def _button(self, interaction: discord.Interaction, _):
        assert self.start is not None
        bot = cast(YoFishing, interaction.client)

        self._button.disabled = True
        await self.message.edit(view=self)
        self.stop()

        duration = time.monotonic() - self.start
        if duration > 1:
            await interaction.response.send_message(
                "The fish appears to have gotten away thanks to your sluggish reaction time. "
                "Next time you must be faster."
            )
        else:
            content = f"Well done! You reeled in after just {duration:.2f} seconds."
            if random.choices([0, 1], [0.75, 0.25])[0]:
                rating = random.choices(
                    list(ItemRating.__members__.values()), [0.35, 0.35, 0.2, 0.1]
                )[0]
                item = random.choices(
                    list(ItemType.__members__.values()), [0.2, 0.2, 0.2, 0.1, 0.1, 0.1]
                )[0]

                content += (
                    f"\nYou found a{'n' if rating == ItemRating.unusual else ''} "
                    f"`{rating._name_.title()} {item._name_.replace('_', ' ').title()}`!"
                )
                await bot.d.execute(
                    "INSERT INTO items VALUES(?, ?, ?, ?);",
                    os.urandom(8).hex(),
                    interaction.user.id,
                    item,
                    rating,
                )
            else:
                content += "\nYou got a fish!"
                await bot.d.execute(
                    "UPDATE users SET fish=fish + 1 WHERE id=?;", interaction.user.id
                )

            await interaction.response.send_message(content)

    async def waiter(self):
        await asyncio.sleep(self.seconds)
        # an ideal hacky method...
        self._button.style = discord.ButtonStyle.green
        self._button.emoji = "\U0001f41f"
        self._button.label = "It appears!"
        self._button.disabled = False

        await self.message.edit(view=self)
        self.start = time.monotonic()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.author:
            return True
        await interaction.response.defer()
        return False

    async def on_timeout(self) -> None:
        self._button.disabled = True
        await self.message.edit(view=self)


class ItemsPaginator(ui.View):
    message: discord.Message

    def __init__(self, items: Sequence[sqlite3.Row]):
        self.items = items
        self.page = 0

        super().__init__(timeout=180)

    @staticmethod
    def build_embed(items: Sequence[sqlite3.Row], start: int = 1) -> discord.Embed:
        return discord.Embed(
            description="\n".join(
                f"{n}. `{ItemRating(item['rating'])._name_.capitalize()} "
                f"{ItemType(item['item'])._name_.capitalize()}`"
                for n, item in enumerate(items[:10], start=start)
            ),
            colour=0xFFFFFF,
        )

    @ui.button(emoji="\U0001F448", style=discord.ButtonStyle.secondary, disabled=True)
    async def _back(self, interaction: discord.Interaction, button: ui.Button):
        self.page -= 1
        if not self.page:
            button.disabled = True
        elif self.page < (len(self.items) // 10) + 1:
            self._forward.disabled = False

        embed = self.build_embed(
            self.items[self.page * 10 : (self.page + 1) * 10],
            start=(self.page + 1) * 10,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(emoji="\u270B", style=discord.ButtonStyle.secondary)
    async def _halt(self, interaction: discord.Interaction, button: ui.Button):
        for child in self.children:
            if isinstance(child, (ui.Button, ui.Select)):
                child.disabled = True

        await interaction.response.edit_message(view=self)
        self.stop()

    @ui.button(emoji="\U0001F449", style=discord.ButtonStyle.secondary)
    async def _forward(self, interaction: discord.Interaction, button: ui.Button):
        self.page += 1
        if self.page >= (len(self.items) // 10) + 1:
            button.disabled = True
        elif self.page > 0:
            self._back.disabled = False

        embed = self.build_embed(
            self.items[self.page * 10 : (self.page + 1) * 10],
            start=(self.page + 1) * 10,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, (ui.Button, ui.Select)):
                child.disabled = True

        await self.message.edit(view=self)


class Fishing(app_commands.Group, name="fishing"):
    def __init__(self, bot: YoFishing):
        self.bot = bot

        super().__init__()

    @app_commands.checks.cooldown(2, 60)
    @app_commands.command(
        name="cast", description="Cast your line out into the realm of fishies"
    )
    async def _cast(self, interaction: discord.Interaction):
        view = CastView(interaction.user, random.randint(3, 7))

        await interaction.response.send_message("Your line has been cast!", view=view)
        view.message = await interaction.original_message()

    @app_commands.command(name="items", description="Look at your lovely items")
    async def _items(self, interaction: discord.Interaction):
        items = await self.bot.d.fetchall(
            "SELECT * FROM items WHERE owner_id=?;", interaction.user.id
        )

        if not items:
            await interaction.response.send_message("You do not own any items!")
        else:
            embed = ItemsPaginator.build_embed(items[:10])

            if len(items) <= 10:
                await interaction.response.send_message(embed=embed)
            else:
                view = ItemsPaginator(items)
                await interaction.response.send_message(embed=embed, view=view)
                view.message = await interaction.original_message()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user = await self.bot.d.fetchone(
            "SELECT * FROM users WHERE id=?;", interaction.user.id
        )
        if user is None:
            description = (
                "Welcome to Yo! Fishing, due to some circumstances (bad design) "
                "I have to check every time someone runs a fishing related command "
                "if they are registered in the bot's database (very bad design!). "
                "You appear not to be in the database (which is why I have to do this), "
                "just run the command again for everything to work perfectly."
            )

            await interaction.response.send_message(
                embed=discord.Embed(description=description, colour=0xFFFFFF)
            )
            await self.bot.d.execute(
                "INSERT INTO users (id) VALUES (?);", interaction.user.id
            )
            return False
        return True


async def setup(bot: YoFishing):
    bot.tree.add_command(Fishing(bot))
