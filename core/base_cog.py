import discord
from discord.ext import commands

from core.logger import get_logger


class BaseCog(commands.Cog):
    logger = get_logger(__name__)

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.db = self.bot.db[self._id]
        self.cache = {}

        # loads the cache from the database
        self.bot.loop.create_task(self.load_cache())

    async def update_db(self):  # updates database with cache using _id
        await self.db.find_one_and_update(
            {"_id": self._id},
            {"$set": self.cache},
                 upsert=True,
        )

    async def load_cache(self):
        db = await self.db.find_one({"_id": self._id})
        update = True

        if db is None:
            db = self.default_cache
        elif db.keys() != self.default_cache.keys(): # if the cache in the database has missing keys add them
            db = self.default_cache | db
        else:
            update = False

        self.cache = db

        if update:
            await self.update_db()

        self.guild: discord.Guild = await self.bot.fetch_guild(self.bot.config["guild_id"])

        # signal that the task is finished by incrementing tasks_done
        self.bot.tasks_done = self.bot.tasks_done + 1

    async def after_load(self): # gets called after cogs have finished loading to avoid exceptions
        pass
