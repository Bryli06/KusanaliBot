import discord
from discord.ext import commands
from discord.ui import Select, View

from discord import ApplicationContext, Colour, Interaction, Permissions, SlashCommandGroup

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel

import re


class AutoMod(BaseCog):
    _id = "automod"

    default_cache = {
        "bannedWords": {

        }
    }

    _bl = SlashCommandGroup("banlist", "Manages banned words.",
                            default_member_permissions=Permissions(manage_messages=True))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.author.guild_permissions.administrator:
            return

        # checks for actions to execute
        delete = False

        final_message = message.content

        for banned_word in self.cache["bannedWords"]:
            # the flags that are used when checking for banned words
            whole = "whole" in self.cache["bannedWords"][banned_word]
            case = "case" in self.cache["bannedWords"][banned_word]

            match = await self.find_banned_word(final_message, banned_word, whole, case)
            if match[0]:
                delete |= "delete" in self.cache["bannedWords"][banned_word]

                final_message = match[1]

        # delete message
        if delete:
            await message.delete()

            dm_channel = await message.author.create_dm()

            embed = discord.Embed(
                description=final_message, colour=Colour.red(), timestamp=message.created_at)
            embed.set_author(
                name=f"{message.author.name}#{message.author.discriminator}", icon_url=message.author.avatar)

            await dm_channel.send(f"Your message was deleted due to it containing a banned word.", embed=embed)

    async def find_banned_word(self, message, banned_word, whole=False, case=False):
        """
        Finds the banned word, if any exist, in the message with the given flags.

        Returns a tuple, if the banned word was found, and the message with banned word censored.

        """

        check_message = message

        # not case sensitive, turn them all to lowercase
        if not case:
            check_message = check_message.lower()
            banned_word = banned_word.lower()

        if whole:
            # matches whole substrings only
            match = re.search(r"\b" + banned_word + r"\b", check_message)
            return (match != None, re.sub(r"\b" + banned_word + r"\b", "\*" * len(banned_word), message))

        # matches any substring
        match = re.search(banned_word, check_message)
        return (match != None, re.sub(banned_word, "\*" * len(banned_word), message))

    @_bl.command(name="add", description="Bans a word with given flags.")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def bl_add(self, ctx: ApplicationContext, banned_word: discord.Option(str, "The word you want to ban.")):
        """
        Ban a word with given flags.

        Flags available:
            delete: Delete the message
            whole: Match whole substrings only
            case: Substring is case sensitive

        """

        # stop if the word has already been banned
        if banned_word in self.cache["bannedWords"]:
            embed = discord.Embed(
                title="Error", description=f"{banned_word} is banned", colour=Colour.red())

            await ctx.respond(embed=embed)
            return

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
                    description="Bans whole messages."
                ),
                discord.SelectOption(
                    label="Case",
                    value="case",
                    description="Bans case sensitive messages."
                )
            ]
        )

        async def _flag_callback(interaction: Interaction):
            self.cache["bannedWords"].update({banned_word: flags.values})
            await self.update_db()

            embed = discord.Embed(
                title="Success", description=f"{banned_word} was added to the banlist.", colour=Colour.green())

            await interaction.response.send_message(embed=embed)

        flags.callback = _flag_callback

        flag_view = View(flags)
        await ctx.respond(view=flag_view, ephemeral=True)

    @_bl.command(name="remove", description="Remove a word from the banlist.")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def bl_remove(self, ctx, banned_word: discord.Option(str, "The word you want to unban.")):
        """
        Remove a word from the banlist.

        """

        if banned_word not in self.cache["bannedWords"]:
            embed = discord.Embed(
                title="Error", description=f"{banned_word} was not banned", colour=Colour.red())

            ctx.respond(embed=embed)
            return

        self.cache["bannedWords"].pop(banned_word)

        await self.update_db()

        embed = discord.Embed(
            title="Success", description=f"{banned_word} was removed from the banlist.", colour=Colour.green())

        await ctx.respond(embed=embed)

    @_bl.command(name="show", description="Lists all the banned words and their flags.")
    @checks.has_permissions(PermissionLevel.MOD)
    async def bl_list(self, ctx: ApplicationContext):
        """
        Lists all the banned words and their flags.

        """

        description = ""
        for banned_word in self.cache["bannedWords"]:
            description += banned_word + ": "

            for flag in self.cache["bannedWords"][banned_word]:
                description += flag + " "

            description += "\n"

        embed = discord.Embed(
            title="Banned words:", description=description, colour=Colour.blue())

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(AutoMod(bot))
