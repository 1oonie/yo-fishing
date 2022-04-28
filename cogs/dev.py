import textwrap
import traceback

import discord
from discord import app_commands, ui

from bot import YoFishing


class EvalModal(ui.Modal, title="Evaluate some code"):
    code = ui.TextInput(label="Code", style=discord.TextStyle.long, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if self.code.value is None:
            await interaction.response.send_message("You must enter some code")
            return

        code = "async def eval_func():" + textwrap.indent(self.code.value, "    ")

        environment = {
            "bot": interaction.client,
            "channel": interaction.channel,
            "guild": interaction.guild,
            "author": interaction.user,
        }
        environment.update(globals())

        exec(code, environment)
        try:
            await environment["eval_func"]()
        except Exception:
            await interaction.response.send_message(
                f"Failed to execute code: ```{traceback.format_exc()}```"
            )
        else:
            await interaction.response.send_message(
                "Successfully executed code", ephemeral=True
            )


class Dev(app_commands.Group, name="dev"):
    def __init__(self, bot: YoFishing):
        self.bot = bot

        super().__init__()

    @app_commands.command(name="sync", description="Sync the tree")
    async def _sync(self, interaction: discord.Interaction):
        await self.bot.tree.sync()
        await interaction.response.send_message("Synced tree successfully")

    @app_commands.command(name="reload", description="Reload an extension")
    @app_commands.describe(extension="The extension to reload")
    async def _reload(self, interaction: discord.Interaction, extension: str):
        try:
            await self.bot.reload_extension(extension)
        except Exception:
            await interaction.response.send_message(
                f"Failed to reload extension: ```{traceback.format_exc()}```"
            )
        else:
            await interaction.response.send_message("Reloaded extension successfully")

    @app_commands.command(name="eval", description="Evaluate some code")
    async def _eval(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EvalModal())

    @app_commands.command(name="sql", description="Evaluate some SQL query")
    async def _sql(self, interaction: discord.Interaction):
        ...

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message(
                "You are not allowed to use this command!", ephemeral=True
            )
            return False
        return True


async def setup(bot: YoFishing):
    bot.tree.add_command(Dev(bot))
