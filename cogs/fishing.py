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

FLOWERS = ["🌺", "🌷", "🌼"]
FISH = {"🐟": 1, "🐠": 5, "🐡": 3, "🦞": 3, "🦀": 4, "🐳": 10}
SHARK = "🦈"
OBJECTS = ["👢", "⚓"]

ITEM_TYPES = [
    "Fishing Rod",
    "Bait",
    "Capitalism Hat",
    "Hammer",
    "Sickle",
    "New New Cheeselandic Flag",
]
ITEM_RATINGS = ["Normal", "Unique", "Strange", "Alan Smith"]


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
        if duration > 3:
            await interaction.response.send_message(
                "The fish appears to have gotten away thanks to your sluggish reaction time. "
                "Next time you must be faster."
            )
        else:
            content = f"Well done! You reeled in after just {duration:.2f} seconds."
            if random.choices([0, 1], [0.75, 0.25])[0]:
                rating = random.choices(list(ITEM_RATINGS), [0.5, 0.3, 0.1, 0.01])[0]
                item = random.choices(
                    list(ITEM_TYPES), [0.2, 0.2, 0.2, 0.1, 0.1, 0.05]
                )[0]

                content += (
                    f"\nYou found a{'n' if rating == 'Alan Smith' else ''} "
                    f"`{rating} {item}`!"
                )
                await bot.d.execute(
                    "INSERT INTO items VALUES(?, ?, ?, ?);",
                    os.urandom(8).hex(),
                    interaction.user.id,
                    ITEM_TYPES.index(item),
                    ITEM_RATINGS.index(rating),
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
    def build_embed(items: Sequence[sqlite3.Row], nitems: int, start: int = 1):
        return f"You have {nitems} item{'s' if nitems != 1 else ''} ```" + "\n".join(
            f"{n}. {ITEM_RATINGS[item['rating']]} {ITEM_TYPES[item['item']]}"
            for n, item in enumerate(items[:10], start=start)
        ) + "```"

    @ui.button(emoji="\U0001F448", style=discord.ButtonStyle.secondary, disabled=True)
    async def _back(self, interaction: discord.Interaction, button: ui.Button):
        self.page -= 1
        if not self.page:
            button.disabled = True
        elif self.page < (len(self.items) // 10) + 1:
            self._forward.disabled = False

        content = self.build_embed(
            self.items[self.page * 10 : (self.page + 1) * 10],
            len(self.items),
            (self.page + 1) * 10
        )
        await interaction.response.edit_message(content=content, view=self)

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

        content = self.build_embed(
            self.items[self.page * 10 : (self.page + 1) * 10],
            len(self.items),
            (self.page + 1) * 10
        )
        await interaction.response.edit_message(content=content, view=self)

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, (ui.Button, ui.Select)):
                child.disabled = True

        await self.message.edit(view=self)


class StaticButton(ui.Button):
    def __init__(self, emoji=None):
        super().__init__(label="\u200b", emoji=emoji, style=discord.ButtonStyle.green)

    async def callback(self, interaction):
        self.disabled = True
        await interaction.response.edit_message(
            view=self.view,
        )


class WaterButton(ui.Button):
    view: "FishingView"

    def __init__(self, count, emoji):
        self.value = emoji
        self.count = count
        super().__init__(label="/" * count, style=discord.ButtonStyle.primary)

    async def callback(self, interaction):
        self.view.picked_up.append(self.value)
        picked_up = ", ".join(self.view.picked_up)

        self.count -= 1
        self.label = "/" * self.count

        if self.count == 0:
            self.disabled = True
            self.label = self.value

        self.view.tries_remaining -= 1

        if self.value == SHARK:
            self.view.disable_all()
            self.view.stop()
            await interaction.response.edit_message(
                view=self.view,
            )
            await interaction.followup.send(
                content=f"Oh no! You hit a {SHARK} :( Your score was {self.view.score}"
            )
            await self.add_fish(interaction)
            return

        elif self.value in OBJECTS:
            await interaction.response.edit_message(
                content=f"You fished up a {self.value}, it is pretty worthless so you won't get anything from it."
                f"\n\nItems fished up so far: {picked_up}\nGoes remaining: {self.view.tries_remaining}"
                f"\nScore: {self.view.score}",
                view=self.view,
            )

        else:
            self.view.score += FISH[self.value]
            await interaction.response.edit_message(
                content=f"You fished up a {self.value}, you get {FISH[self.value]} points for that!\n\n"
                f"Items fished up so far: {picked_up}\nGoes remaining: {self.view.tries_remaining}"
                f"\nScore: {self.view.score}",
                view=self.view,
            )

        self.value = WaterButton.get_emoji()

        if self.view.tries_remaining == 0:
            self.view.stop()
            self.view.disable_all()

            await self.view.message.edit(view=self.view)
            await interaction.followup.send(
                f"Your game is over! You scored a total of {self.view.score} points without hitting a shark!"
                f"\nThat means you get {self.view.score} additional fish!"
            )
            await self.add_fish(interaction)

    @staticmethod
    def get_emoji():
        return random.choice(
            random.choices([list(FISH.keys()), SHARK, OBJECTS], weights=[1, 0.1, 0.75])[
                0
            ]
        )

    async def add_fish(self, interaction: discord.Interaction):
        bot = cast(YoFishing, interaction.client)
        await bot.d.execute(
            "UPDATE users SET fish=fish + ? WHERE id=?;",
            self.view.score,
            interaction.user.id,
        )


class FishingView(ui.View):
    message: discord.Message

    def __init__(self, author, *args, **kwargs):
        self.author = author

        super().__init__(*args, **kwargs)

        for _ in range(25):
            type_ = random.choices([WaterButton, StaticButton], weights=[1, 0.6])[0]
            if type_ is StaticButton:
                instance = StaticButton(
                    emoji=random.choices(
                        [None, random.choice(FLOWERS)], weights=[1, 2]
                    )[0]
                )
            else:
                instance = WaterButton(
                    emoji=WaterButton.get_emoji(), count=random.randint(1, 3)
                )

            self.add_item(instance)

        self.tries_remaining = 10
        self.score = 0
        self.picked_up = []

    def disable_all(self):
        for child in self.children:
            if isinstance(child, ui.Button):
                child.disabled = True

    async def interaction_check(self, interaction):
        if interaction.user.id == self.author.id:
            return True
        else:
            await interaction.response.send_message(
                content="This is not your game of fishing!", ephemeral=True
            )
            return False

    async def on_timeout(self):
        await self.message.edit(
            content=f"Timed out due to lack of interaction, score was {self.score}",
            view=None,
        )


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
        view.message = await interaction.original_response()

    @app_commands.checks.cooldown(2, 60)
    @app_commands.command(
        name="minigame", description="The original Yo! Fishing minigame"
    )
    async def _minigame(self, interaction: discord.Interaction):
        view = FishingView(interaction.user, timeout=60)
        await interaction.response.send_message(content="Play fishing!", view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="stats", description="Epic fishy statistics")
    async def _stats(
        self, interaction: discord.Interaction, user: Optional[discord.Member] = None
    ):
        statee = user or interaction.user
        udata = await self.bot.d.fetchone(
            "SELECT * FROM users WHERE id=?;", statee.id
        )

        if udata is None:
            await interaction.response.send_message(
                f"{statee.mention} run a Yo! Fishing command right now so that {interaction.user} can see your stats."
            )
            return

        await interaction.response.send_message(
            f"```username : {statee.name}\nbalance  : {udata['balance']}\nfish     : {udata['fish']}"
            f"\nxp       : {udata['xp']}\n\nThank you for choosing Fishing incorporated.```"
        )

    @app_commands.command(name="items", description="Look at your lovely items")
    async def _items(self, interaction: discord.Interaction):
        items = await self.bot.d.fetchall(
            "SELECT * FROM items WHERE owner_id=?;", interaction.user.id
        )

        if not items:
            await interaction.response.send_message("You do not own any items!")
        else:
            content = ItemsPaginator.build_embed(items[:10], len(items))

            if len(items) <= 10:
                await interaction.response.send_message(content)
            else:
                view = ItemsPaginator(items)
                await interaction.response.send_message(content, view=view)
                view.message = await interaction.original_response()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user = await self.bot.d.fetchone(
            "SELECT * FROM users WHERE id=?;", interaction.user.id
        )
        if user is None:
            await self.bot.d.execute(
                "INSERT INTO users (id) VALUES (?);", interaction.user.id
            )
        await self.bot.d.execute(
            "UPDATE users SET xp=xp + 1 WHERE id=?;", interaction.user.id
        )

        return True


async def setup(bot: YoFishing):
    bot.tree.add_command(Fishing(bot))
