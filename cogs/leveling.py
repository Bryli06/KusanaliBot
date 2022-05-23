import discord
from discord.ext import commands

from core.checks import PermissionLevel
from core import calculate_level, checks
from core.logger import get_logger

from collections import OrderedDict
logger = get_logger(__name__)


class Leveling(commands.Cog):
    _id = "leveling"

    exp_given = 1

    default_cache = {
        "userExpData": {

        }
    }

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.api.get_plugin_partition(self)
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

        await self.update_exp(message.channel, message.author)

    @commands.group(name="rank", aliases=['level'], usage="[user]")
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def rank(self, ctx, user: discord.User = None):
        """
        Gets the rank of a user.

        You may leave 'user' blank to get your own rank.

        """

        if user == None:
            user = ctx.author

        cache = self.cache["userExpData"]
        sort = sorted(cache.items(), key=lambda x: x[1], reverse=True)

        rank = 0
        exp = 0

        for key, value in sort:
            rank += 1
            if key == str(user.id):
                exp = value

                break

        embed = discord.Embed(
            title=user.display_name,
            description=f"**Level:** {calculate_level.get_level(exp)} \n **Exp:** {exp}/{calculate_level.next_level(exp)} \n **Rank:** {rank}",
            color=self.bot.main_color
        )

        embed.set_thumbnail(url=user.avatar_url)

        await ctx.send(embed=embed)

    @commands.command(name="setlevel")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def set_rank(self, ctx, user: discord.User, level: int):
        """
        Sets the level of a user.

        """

        self.cache["userExpData"][str(
            user.id)] = calculate_level.level_to_exp(level)

        await self.update_db()

        embed = discord.Embed(
            title="Success.",
            description=f"{user.mention}'s level was set to {level}.",
            color=self.bot.main_color
        )

        await ctx.send(embed=embed)

    @commands.group(name="top", aliases=['leaderboard', 'lb'])
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def top(self, ctx, page: int = 1):
        """
        Gets the top 10 users in the server.

        Run `{prefix}top [number]` to get the next 10 users starting at rank [number].

        Run `{prefix}top me` to get the people around you in level.

        """

        start = (page - 1) * 10
        end = start + 10

        cache = self.cache["userExpData"]

        sort = sorted(cache.items(), key=lambda x: x[1], reverse=True)[
            start: end]

        description = ""

        rank = start + 1
        for key, value in sort:
            description += f"**#{rank}.** <@{key}>\n\t Level: `{calculate_level.get_level(int(value))}` \n\t Exp `{value}/{calculate_level.next_level(int(value))}`\n"
            rank += 1

        embed = discord.Embed(
            title=f"{ctx.guild.name}'s leaderboard",
            description=description,
            color=self.bot.main_color
        )

        await ctx.send(embed=embed)

    async def update_exp(self, channel, user):
        messages = (await channel.history(limit=10).flatten())[1:]

        for message in messages:
            if not message.author.bot:
                if message.author != user:
                    await self.add_exp(user.id)

                return

    async def add_exp(self, userId):
        if str(userId) not in self.cache["userExpData"]:
            self.cache["userExpData"][str(userId)] = self.exp_given
            await self.update_db()

            return

        self.cache["userExpData"][str(userId)] += self.exp_given
        await self.update_db()


def setup(bot):
    bot.add_cog(Leveling(bot))
