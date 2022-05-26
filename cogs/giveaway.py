import discord
from discord.ext import commands
from discord.ui import Select, View

from discord import ApplicationContext, Interaction, OptionChoice, SlashCommandGroup

from core import checks
from core.checks import PermissionLevel

from core.logger import get_logger

from datetime import date, datetime, timedelta
import time

from threading import Timer

logger = get_logger(__name__)


class Giveaway(commands.Cog):
    _id = "giveaway"

    default_cache = {
        "giveaways": {

        }
    }

    _ga = SlashCommandGroup("giveaway", "Contains all giveaway commands.")

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

    def giveaway_end(self, message: Interaction):
        embed = discord.Embed(title="Giveaway", description="Giveaway ended")
        self.bot.loop.create_task(message.edit_original_message(embed=embed))

    @_ga.command(name="create", description="Creates a new giveaway")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _ga_create(self, ctx: ApplicationContext, seconds: discord.Option(int, "Time in seconds.", min_value=5)):
        unix_now = int(time.mktime(datetime.now().timetuple()))
        offset = int(timedelta(0, seconds).total_seconds())

        embed = discord.Embed(
            title="Giveaway", description=f"Giveaway started and will end at <t:{unix_now + offset}:F>")
        message = await ctx.respond(embed=embed)

        th = Timer(offset, self.giveaway_end, {message})
        th.start()


def setup(bot):
    bot.add_cog(Giveaway(bot))
