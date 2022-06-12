import random

import discord
from discord.ext import commands
from discord.ui import Select, Button, View

from discord import ApplicationContext, Colour, Interaction, Permissions, SlashCommandGroup, TextChannel

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel

from datetime import datetime
import time

from copy import deepcopy


class Giveaway(BaseCog):
    _id = "giveaway"

    default_cache = {
        "giveaways": {

        }
    }

    _ga = SlashCommandGroup("giveaway", "Contains all giveaway commands.",
                            default_member_permissions=Permissions(manage_messages=True))

    async def after_load(self):
        await self.start_countdowns()

    async def start_countdowns(self):
        """
        Starts all giveaway countdowns. Used when the bot goes online.

        """

        # copied to avoid exceptions from removing done giveaways while iterating
        cache = deepcopy(self.cache["giveaways"])
        for message_id in cache:
            await self.start_countdown(int(message_id))

    async def start_countdown(self, message_id):
        """
        Starts a giveaway countdown given the giveaway ID taken from the message of the giveaway.

        """

        # get the channel the giveaway is in
        channel: TextChannel = await self.guild.fetch_channel(
            self.cache["giveaways"][str(message_id)]["channel"])

        # try fetching the message
        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            self.bot.dispatch("error", e,
                              f"There seems to be an active giveaway in {channel.mention} that the bot cannot access.",
                              f"Delete the giveaway in {channel.mention} manually `ID: {message_id}`.")

            self.cache["giveaways"].pop(str(message_id))
            await self.update_db()

            return

        # update the button, otherwise it won't work
        await self.add_enter_button(message)

        # get time remaining in computer time
        unix = self.cache["giveaways"][str(
            message_id)]["unixTime"] - datetime.now().timestamp()

        # add task to close giveaway after countdown has finished
        self.bot.loop.call_later(unix, self.giveaway_end, message)

    async def add_enter_button(self, message: discord.Message):
        """
        Adds an enter button for giveaways.

        """

        async def _enter_callback(interaction: Interaction):
            giveaway = self.cache["giveaways"][str(message.id)]

            # stops if user has already joined giveaway
            if interaction.user.id in giveaway["participants"]:
                embed = discord.Embed(
                    title="Error", description="You can't enter more than once.", colour=Colour.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            # stops if user does not have any of the roles needed to enter
            if not any(role.id in giveaway["allowedRoles"] for role in interaction.user.roles):
                embed = discord.Embed(
                    title="Error", description="You do not possess any of the roles needed to enter.", colour=Colour.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            # adds user to the participants list
            giveaway["participants"].append(interaction.user.id)
            await self.update_db()

            embed = discord.Embed(
                title="Success", description="You've entered the giveaway!", colour=Colour.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)

        enter = Button(label="Enter", style=discord.ButtonStyle.blurple)
        enter.callback = _enter_callback

        enter_view = View(enter)

        await message.edit(view=enter_view)

    def giveaway_end(self, message: discord.Message):
        """
        Ends the giveaway from the message.

        """

        if message == None or str(message.id) not in self.cache["giveaways"]:
            return

        cache = self.cache["giveaways"][str(message.id)]

        reward = cache["reward"]
        winners = cache["winners"]
        allowed_roles = cache["allowedRoles"]
        participants = cache["participants"]

        # end giveaway with no winners
        if len(participants) == 0:
            embed = discord.Embed(
                title="Giveaway has ended!", description="The giveaway has ended with no winners.", colour=Colour.blue())

            self.bot.loop.create_task(message.edit(embed=embed, view=None))

            self.cache["giveaways"].pop(str(message.id))
            self.bot.loop.create_task(self.update_db())

            return

        winner_ids = []

        # all participants win if the number of winners is greater than the number of participants
        if winners >= len(participants):
            winner_ids = participants
        else:
            for i in range(winners):
                winner_id = random.choice(participants)

                winner_ids.append(winner_id)
                participants.remove(winner_id)

        description = "Congratulations to:\n"
        for winner_id in winner_ids:
            description += f"<@{winner_id}> "

        description += f"for winning a `{reward}`!"

        embed = message.embeds[0]

        # edit embed to end giveaway
        embed.title = f"The {reward} giveaway has ended!"
        embed.description = description
        embed.clear_fields()

        self.bot.loop.create_task(message.edit(embed=embed, view=None))

        self.cache["giveaways"].pop(str(message.id))
        self.bot.loop.create_task(self.update_db())

    @commands.message_command(name="End giveaway")
    @checks.has_permissions(PermissionLevel.EVENT_ADMIN)
    async def message_giveaway_end(self, ctx, message):
        """
        End a giveaway before its time.

        """

        # stop if the message is not a giveaway
        if str(message.id) not in self.cache["giveaways"]:
            embed = discord.Embed(
                title="Error", description="Message is not an active giveaway.")
            await ctx.respond(embed=embed, ephemeral=True)

            return

        self.giveaway_end(message)

        embed = discord.Embed(
            title="Success", description="Giveaway was ended.", colour=Colour.green())
        await ctx.respond(embed=embed, ephemeral=True)

    @_ga.command(name="create", description="Creates a new giveaway")
    @checks.has_permissions(PermissionLevel.EVENT_ADMIN)
    async def _ga_create(self, ctx: ApplicationContext, reward: discord.Option(str, "The name of the reward."),
                         winners: discord.Option(int, "The number of winners.", min_value=1),
                         minutes: discord.Option(int, "Minutes.", min_value=0, default=0),
                         hours: discord.Option(int, "Hours.", min_value=0, default=0),
                         days: discord.Option(int, "Days.", min_value=0, default=0)):
        """
        Creates a new giveaway.

        """

        duration = 60 * (minutes + 60 * (hours + 24 * days))

        # stop if amount is 0
        if duration == 0:
            embed = discord.Embed(
                title=f"Error", description="Time cannot be 0.", colour=Colour.red())
            ctx.respond(embed=embed)

            return

        # limits the roles shown to 25
        allowed_roles = Select(
            placeholder="Select allowed roles",
            max_values=len(self.bot.config["levelRoles"]) if len(
                self.bot.config["levelRoles"]) <= 25 else 25,
            options=[discord.SelectOption(label=(await self.guild._fetch_role(role)).name, value=str(
                role)) for role in self.bot.config["levelRoles"]][:25]
        )

        async def _roles_callback(interaction: Interaction):
            unix = int(time.mktime(datetime.now().timetuple())) + duration

            giveaway = {
                "channel": ctx.channel_id,
                "unixTime": unix,
                "reward": reward,
                "winners": winners,
                "allowedRoles": [int(role) for role in allowed_roles.values],
                "participants": []
            }

            embed = discord.Embed(
                title=f"{reward} giveaway!", description=f"A giveaway has started and will end on <t:{unix}:F>!\n{winners} participant{'s' if winners > 1 else ''} will be selected at the end.", colour=Colour.blue())

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

            await self.add_enter_button(message)

            await self.start_countdown(message.id)

        allowed_roles.callback = _roles_callback

        roles_view = View(allowed_roles)

        await ctx.respond(view=roles_view, ephemeral=True)


def setup(bot):
    bot.add_cog(Giveaway(bot))
