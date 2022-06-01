import discord
from discord.ext import commands
from discord.ui import Select, View

from discord import ApplicationContext, Interaction, OptionChoice, SlashCommandGroup

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel


class AutoMod(BaseCog):
    _id = "automod"

    default_cache = {
        "bannedWords": {

        }
    }

    _bl = SlashCommandGroup("blacklist", "Manages blacklisted words.")

    def __init__(self, bot) -> None:
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        delete = False

        for banned_word in self.cache["bannedWords"]:
            whole = "whole" in self.cache["bannedWords"][banned_word]
            case = "case" in self.cache["bannedWords"][banned_word]

            if await self.find_banned_word(message, banned_word, whole, case):
                delete |= "delete" in self.cache["bannedWords"][banned_word]
                break

        # delete message
        if delete:
            await message.delete()

            dm_channel = await message.author.create_dm()
            await dm_channel.send("Your message was deleted due to it containing a banned word.")

    async def find_banned_word(self, message, banned_word, whole=False, case=False):
        content = message.content

        if not case:
            content = content.lower()
            banned_word = banned_word.lower()

        if whole:
            words = content.split(' ')

            for word in words:
                if word == banned_word:
                    return True

            return False

        return banned_word in content

    # Adds a word to the blacklist. Takes in a word to word/phrase to blacklist first followed by flags. Flags will start with the prefix %. Possible flags include %whole, %delete, %warn, etc.
    @_bl.command(name="add", description="Blacklist a word with given flags.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def bl_add(self, ctx: ApplicationContext, banned_word: discord.Option(str, "The word you want to ban.")):
        """
        Blacklist a word with given flags.

        """

        flags = Select(
            placeholder="Select flags",
            min_values=1,
            max_values=3,
            options=[
                discord.SelectOption(
                    label="Delete",
                    value="delete",
                    description="Deletes the message."
                ),
                discord.SelectOption(
                    label="Whole",
                    value="whole",
                    description="Blacklists whole messages."
                ),
                discord.SelectOption(
                    label="Case",
                    value="case",
                    description="Blacklists case sensitive messages."
                )
            ]
        )

        if banned_word in self.cache["bannedWords"]:
            embed = discord.Embed(
                title="Word already banned",
                description=f"{banned_word} is blacklisted"
            )

            await ctx.respond(embed=embed)
            return

        async def _flag_callback(interaction: Interaction):
            self.cache["bannedWords"].update({banned_word: flags.values})
            await self.update_db()

            embed = discord.Embed(
                title="Success!",
                description=f"{banned_word} was added to the blacklist."
            )

            await interaction.response.send_message(embed=embed)

        flags.callback = _flag_callback

        flag_view = View(flags)
        await ctx.respond(view=flag_view, ephemeral=True)

    @_bl.command(name="remove", description="Remove a word from the blacklist.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def bl_remove(self, ctx, banned_word: discord.Option(str, "The word you want to unban.")):
        """
        Remove a word from the blacklist.

        """

        if self.cache["bannedWords"].pop(banned_word, "Word not found") == "Word not found":
            embed = discord.Embed(
                title="Error: Argument not found",
                description=f"{banned_word} was not blacklisted"
            )

            ctx.respond(embed=embed)
            return

        await self.update_db()

        embed = discord.Embed(
            title="Success!",
            description=f"{banned_word} was removed from blacklist."
        )

        await ctx.respond(embed=embed)

    # Lists all the banned words in the cache
    @_bl.command(name="list", description="Lists all the blacklisted words and their flags.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def bl_list(self, ctx: ApplicationContext):
        """
        Lists all the blacklisted words and their flags.

        """

        message = ""
        for banned_word in self.cache["bannedWords"]:
            message += banned_word + ": "

            for flag in self.cache["bannedWords"][banned_word]:
                message += flag + " "

            message += "\n"

        embed = discord.Embed(
            title="Blacklisted words:",
            description=message
        )

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(AutoMod(bot))
