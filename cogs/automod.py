import imp
from random import choice, choices
import discord
from discord.ext import commands

from discord import OptionChoice, SlashCommandGroup as slashgroup

from core.checks import PermissionLevel
from core import checks

from core.logger import get_logger

logger = get_logger(__name__)


class AutoMod(commands.Cog):
    _id = "automod"

    testbot: commands.Bot = None

    # can also be warn ban kick mute but not implemented yet
    valid_flags = {OptionChoice("Delete", "delete"), OptionChoice(
        "Whole", "whole"), OptionChoice("Case", "case")}

    guild_ids = {}

    default_cache = {  # can also store more stuff like warn logs or notes for members if want to implement in future
        "bannedWords": {  # dictionary of word and an array of it's flags

        }
    }

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.api.get_collection(self._id)
        self.cache = {}

        self.testbot = self.bot

        self.guild_ids = {977013237889523712}
        logger.debug(f"{self.guild_ids}")

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

    @testbot.slash_command(guild_ids=[977013237889523712])
    async def test(self, ctx):
        await ctx.send("Works!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await message.channel.send(f"{self.guild_ids}")

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
    
    


def setup(bot):
    bot.add_cog(AutoMod(bot))
