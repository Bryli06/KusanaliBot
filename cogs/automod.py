import discord
from discord.ext import commands

from core.checks import PermissionLevel
from core import checks


class AutoMod(commands.Cog):
    _id = "automod"

    # can also be warn ban kick mute but not implemented yet
    valid_flags = {'delete', 'whole', 'case', }

    default_cache = {  # can also store more stuff like warn logs or notes for members if want to implement in future
        "bannedWords": {  # dictionary of word and an array of it's flags

        }
    }

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.api.get_collection(self._id)
        self.cache = {}

        self.bot.loop.create_task(self.load_cache())  # this only runs once xD

    async def update_db(self):  # updates database with cache
        await self.db.find_one_and_update(
            {"_id": self._id},
            {"$set": self.cache},
            upsert=True,
        )

    async def load_cache(self):
        await self.bot.wait_for_connected()

        db = await self.db.find_one({"_id": self._id})
        if db is None:
            db = self.default_cache

        self.cache = db

    @commands.Cog.listener()
    async def on_message(self, message):
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

    @commands.group(name="blacklist", aliases=['bl'], invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _bl(self, ctx):
        """
        Manages blacklisted words.

        First, to blacklist a word, use the command:
        - `{prefix}bl add blacklisted_word flags`

        Current flags supported include:
        - %whole (makes sure that the blacklisted word is alone)
        - %delete (deletes all blacklisted words)
        - %case (case sensitive searching)

        """

        return await ctx.send_help("blacklist")

    # Adds a word to the blacklist. Takes in a word to word/phrase to blacklist first followed by flags. Flags will start with the prefix %. Possible flags include %whole, %delete, %warn, etc.
    @_bl.command(name="add")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def bl_add(self, ctx, *, arg):
        """
        Blacklist a word with given flags.
        """
        args = arg.split(' %')

        if args[0] in self.cache["bannedWords"]:
            await ctx.send("Word already blacklisted")
            return

        # checks if each flag is a valid flag
        for flag in args[1:]:
            if flag not in self.valid_flags:
                await ctx.send(f"Invalid flag: {flag}")
                return

        self.cache["bannedWords"].update({args[0]: args[1:]})
        await self.update_db()
        await ctx.send("Banned word added!")

    @_bl.command(name="remove")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def bl_remove(self, ctx, arg):
        """
        Remove a word from the blacklist.
        """

        if self.cache["bannedWords"].pop(arg, "Word not found") == "Word not found":
            embed = discord.Embed(
                title="Error: Argument not found",
                description=f"{arg} was not blacklisted",
                color=self.bot.error_color,
            )

            ctx.send(embed=embed)
            return

        await self.update_db()
        embed = discord.Embed(
            title="Success.",
            description=f"{arg} was removed from blacklist.",
            color=self.bot.main_color,
        )

        await ctx.send(embed=embed)

    # Lists all the banned words in the cache
    @_bl.command(name="list")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def bl_list(self, ctx):
        """
        List all blacklisted words and their flags.
        """

        message = ""
        for banned_word in self.cache["bannedWords"]:
            message += banned_word + ": "

            for flag in self.cache["bannedWords"][banned_word]:
                message += flag + " "

            message += "\n"

        embed = discord.Embed(
            title="Blacklisted words:",
            description=message,
            color=self.bot.main_color
        )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(AutoMod(bot))
