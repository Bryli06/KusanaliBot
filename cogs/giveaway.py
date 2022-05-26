import discord
from discord.ext import commands
from discord.ui import Select, Button, View

from discord import ApplicationContext, ChannelType, Interaction, OptionChoice, SlashCommandGroup, TextChannel, message_command

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
        channel: TextChannel = guild.get_channel(
            self.cache["giveaways"][str(message_id)]["channel"])
        message = await channel.fetch_message(message_id)

        await self.add_button(message)

        unix = self.cache["giveaways"][str(
            message_id)]["unixTime"] - int(time.mktime(datetime.now().timetuple()))

        th = Timer(unix, self.giveaway_end, {message})
        th.start()

    async def add_button(self, message: discord.Message):
        async def _enter_callback(interaction: Interaction):
            cache = self.cache["giveaways"][str(message.id)]

            if interaction.user.id in cache["participants"]:
                embed = discord.Embed(
                    title="You've already joined this giveaway", description="You can't enter more than once.")
                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            cache["participants"].append(interaction.user.id)
            await self.update_db()

            embed = discord.Embed(title="Success", description="You've entered the giveaway!")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        enter = Button(label="Enter", style=discord.ButtonStyle.blurple)
        enter.callback = _enter_callback

        enter_view = View(enter)

        await message.edit(view=enter_view)

    def giveaway_end(self, message: discord.Message):
        if message == None or str(message.id) not in self.cache["giveaways"]:
            return

        embed = discord.Embed(title="Giveaway", description="Giveaway ended")
        self.bot.loop.create_task(message.edit(embed=embed, view=None))

        self.cache["giveaways"].pop(str(message.id))
        self.bot.loop.create_task(self.update_db())

    @commands.message_command(name="End giveaway")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def message_giveaway_end(self, ctx, message):
        self.giveaway_end(message)

        embed = discord.Embed(title="Success", description="Giveaway was ended")
        await ctx.respond(embed=embed, ephemeral=True)

    @_ga.command(name="create", description="Creates a new giveaway")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _ga_create(self, ctx: ApplicationContext, reward: discord.Option(str, "The name of the reward."),
                         winners: discord.Option(int, "The number of winners.", min_value=1),
                         seconds: discord.Option(int, "For how long you wish the giveaway to stay up.", min_value=1)):
        allowed_roles = Select(
            placeholder="Select allowed roles",
            max_values=25,
            options=[discord.SelectOption(label=role.name, value=str(role.id)) for role in sorted(
                ctx.guild.roles, key=lambda r: -len(r.members))][1:26]
        )

        async def _roles_callback(interaction: Interaction):
            unix = int(time.mktime(datetime.now().timetuple())) + seconds

            giveaway = {
                "channel": ctx.channel_id,
                "unixTime": unix,
                "reward": reward,
                "winners": winners,
                "allowedRoles": [int(role) for role in allowed_roles.values],
                "participants": []
            }

            embed = discord.Embed(
                title=f"{reward} giveaway!", description=f"A giveaway has started and will end on <t:{unix}:F>!\n{winners} participant{'s' if winners > 1 else ''} will be selected at the end.")

            embed.set_author(
                name=f"Host: {ctx.author.display_name}", icon_url=ctx.author.display_avatar)

            value = ""
            for role in allowed_roles.values:
                value += f"<@&{role}> "

            embed.add_field(name="Roles allowed to participate", value=value)

            inter = await interaction.response.send_message(embed=embed)
            message = await inter.original_message()

            self.cache["giveaways"].update({str(message.id): giveaway})
            await self.update_db()

            await self.add_button(message)

            await self.start_thread(message.id)

        allowed_roles.callback = _roles_callback

        roles_view = View(allowed_roles)
        await ctx.respond(view=roles_view, ephemeral=True)


def setup(bot):
    bot.add_cog(Giveaway(bot))
