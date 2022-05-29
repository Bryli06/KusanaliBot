import discord
from discord.ext import commands


class BaseCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db[self._id]
        self.cache = {}

        self.bot.loop.create_task(self.load_cache())

    async def update_db(self):  # updates database with cache
        await self.db.find_one_and_update(
            {"_id": self._id},
            {"$set": self.cache},
            upsert=True,
        )

    async def load_cache(self):
        db = await self.db.find_one({"_id": self._id})
        if db is None:
            db = self.default_cache

        self.cache = db
