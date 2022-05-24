from typing_extensions import Required
import discord
from discord.ext import commands

from core.checks import PermissionLevel
from core import calculate_level, checks
from core.logger import get_logger

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
        self.db = self.bot.db[self._id]
        self.cache = {}

        self.bot.loop.create_task(self.load_cache())  # this only runs once xD

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

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        await self.update_exp(message.channel, message.author)

    @commands.slash_command(name="rank", description="Gets the rank of a user.")
    async def rank(self, ctx, user: discord.Option(discord.User, "The user whose rank you want to see, leave it blank to see yours.", required=False)):
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
            description=f"**Level:** {calculate_level.get_level(exp)} \n **Exp:** {exp}/{calculate_level.next_level(exp)} \n **Rank:** {rank}"
        )

        embed.set_thumbnail(url=user.display_avatar.url)

        await ctx.respond(embed=embed)

    @commands.slash_command(name="setlevel", description="Set the level of the user to a specified value.")
    async def set_rank(self, ctx,
                       user: discord.Option(discord.User, "The user whose level you wish to change."),
                       level: discord.Option(int, "The level you wish to change the user's to")):
        """
        Sets the level of a user.

        """

        self.cache["userExpData"][str(
            user.id)] = calculate_level.level_to_exp(level)

        await self.update_db()

        embed = discord.Embed(
            title="Success!",
            description=f"{user.mention}'s level was set to {level}."
        )

        await ctx.respond(embed=embed)

    @commands.slash_command(name="leaderboard", description="Gets a list of users ordered by level.")
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def top(self, ctx, page: discord.Option(int, "The page you wish to view.", default=1)):
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
            description=description
        )

        await ctx.respond(embed=embed)

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
