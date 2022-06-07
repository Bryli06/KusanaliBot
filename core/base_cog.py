import asyncio
import discord
from discord.ext import commands

from core.logger import get_logger


class BaseCog(commands.Cog):
    logger = get_logger(__name__)

    def __init__(self, bot):
        self.bot: commands.Bot = bot
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

        self.guild: discord.Guild = await self.bot.fetch_guild(self.bot.config["guild_id"])

        self.bot.tasks_done = self.bot.tasks_done + 1

    async def after_load(self):
        pass
