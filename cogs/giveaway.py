import discord
from discord.ext import commands
from discord.ui import Select, View

from discord import ApplicationContext, ChannelType, Interaction, OptionChoice, SlashCommandGroup, TextChannel

from core import checks
from core.checks import PermissionLevel

from core.logger import get_logger

from datetime import date, datetime, timedelta
import time

from threading import Timer

from copy import deepcopy

logger = get_logger(__name__)


class Giveaway(commands.Cog):
    _id = "giveaway"

    _guild_id = 849762277041504286

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
        
        self.cache = db

        await self.start_threads()

    async def start_threads(self):
        cache = deepcopy(self.cache["giveaways"])
        for message_id in cache:
            await self.start_thread(int(message_id))

    async def start_thread(self, message_id):
        guild: discord.Guild = self.bot.get_guild(self._guild_id)
        channel: TextChannel = guild.get_channel(self.cache["giveaways"][str(message_id)]["channel"])
        message = await channel.fetch_message(message_id)

        unix = self.cache["giveaways"][str(message_id)]["unixTime"] - int(time.mktime(datetime.now().timetuple()))

        th = Timer(unix, self.giveaway_end, {message})
        th.start()

    def giveaway_end(self, message: discord.Message):
        if message == None:
            return

        embed = discord.Embed(title="Giveaway", description="Giveaway ended")
        self.bot.loop.create_task(message.edit(embed=embed))

        self.cache["giveaways"].pop(str(message.id))
        self.bot.loop.create_task(self.update_db())

    @_ga.command(name="create", description="Creates a new giveaway")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _ga_create(self, ctx: ApplicationContext, seconds: discord.Option(int, "Time in seconds.", min_value=5)):
        unix_now = int(time.mktime(datetime.now().timetuple()))
        offset = int(timedelta(0, seconds).total_seconds())

        embed = discord.Embed(
            title="Giveaway", description=f"Giveaway started and will end at <t:{unix_now + offset}:F>")
        interaction = await ctx.respond(embed=embed)
        message = await interaction.original_message()

        giveaway = {
            "channel": ctx.channel_id,
            "unixTime": unix_now + offset
        }

        self.cache["giveaways"].update({str(message.id): giveaway})
        await self.update_db()

        await self.start_thread(message.id)


def setup(bot):
    bot.add_cog(Giveaway(bot))
