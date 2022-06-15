import asyncio
import copy
from math import ceil
import random
from wsgiref.headers import tspecials

import discord
from discord.ext import commands
from discord.ui import Select, Button, View, Modal, InputText

from discord import ApplicationContext, Colour, Embed, Interaction, Permissions, SlashCommandGroup, TextChannel

from core import checks
from core.time import TimeConverter, InvalidTime
from core.base_cog import BaseCog
from core.checks import PermissionLevel

from datetime import datetime
import time

from copy import deepcopy


class Giveaway(BaseCog):
    _id = "giveaway"

    default_cache = {
        "tickets": {

        },

        "giveaways": {

        }
    }

    _ga = SlashCommandGroup("giveaway", "Contains all giveaway commands.",
                            default_member_permissions=Permissions(manage_messages=True))
    _tc = _ga.create_subgroup("tickets", "Contains all tickets commands.")

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

        enter_view = View(enter, timeout=None)

        await message.edit(view=enter_view)

    def giveaway_end(self, message: discord.Message):
        """
        Calls asynchronous function to end giveaway.

        """

        self.bot.loop.create_task(self._giveaway_end(message))

    async def _giveaway_end(self, message: discord.Message):
        """
        Ends an active giveaway.
        
        """

        if message == None or str(message.id) not in self.cache["giveaways"]:
            return

        cache = self.cache["giveaways"][str(message.id)]

        reward = cache["reward"]
        winners = cache["winners"]
        allowed_roles = cache["allowedRoles"]
        participants = cache["participants"]

        weights = []

        member_ids = copy.deepcopy(participants)
        for member_id in member_ids:
            try:
                member = await self.guild.fetch_member(member_id)
            except Exception:
                participants.remove(member_id)

                continue

            all_tickets = [0]
            for role_id in self.bot.config["levelRoles"]:
                if role_id in allowed_roles:
                    if member.get_role(role_id):
                        if str(role_id) in self.cache["tickets"]:
                            all_tickets.append(self.cache["tickets"][str(role_id)])
                        else:
                            all_tickets.append(1)

            weights.append(max(all_tickets))

        # end giveaway with no winners
        if len(participants) == 0:
            embed = discord.Embed(
                title="Giveaway has ended!", description="The giveaway has ended with no winners.", colour=Colour.blue())

            await message.edit(embed=embed, view=None)

            self.cache["giveaways"].pop(str(message.id))
            await self.update_db()

            return

        winner_ids = []

        # all participants win if the number of winners is greater than the number of participants
        if winners >= len(participants):
            winner_ids = participants
        else:
            for i in range(winners):
                winner_id = random.choices(participants, weights)[0]

                winner_ids.append(winner_id)

                index = participants.index(winner_id)

                participants.pop(index)
                weights.pop(index)

        description = "Congratulations to:\n"
        for winner_id in winner_ids:
            description += f"<@{winner_id}> "

        description += f"for winning a `{reward}`!"

        embed = message.embeds[0]

        # edit embed to end giveaway
        embed.title = f"The {reward} giveaway has ended!"
        embed.description = description
        embed.clear_fields()

        await message.edit(embed=embed, view=None)

        self.cache["giveaways"].pop(str(message.id))
        await self.update_db()

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
                         end: discord.Option(str, "How long is the giveaway.")):
        """
        Creates a new giveaway.

        """
        duration = 0
        try:
            duration = TimeConverter(end)

        except InvalidTime as e:
            embed = discord.Embed(
                title="error", description=e, colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        # stop if amount is 0
        if duration == 0:
            embed = discord.Embed(
                title=f"Error", description="Time cannot be 0.", colour=Colour.red())
            ctx.respond(embed=embed)

            return

        # limits the roles shown to 25
        allowed_roles = None

        allowed_roles = Select(
            placeholder="Select allowed roles",
            max_values=len(self.bot.config["levelRoles"]) if len(
                self.bot.config["levelRoles"]) <= 25 else 25,
            options=[discord.SelectOption(label=(await self.guild._fetch_role(role)).name, value=str(
                role)) for role in self.bot.config["levelRoles"]][:25]
        )

        async def _roles_callback(interaction: Interaction):
            unix = int(duration.final.timestamp())

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

    @_tc.command(name="list", description="Shows tickets for all roles.")
    @checks.has_permissions(PermissionLevel.EVENT_ADMIN)
    async def _tc_list(self, ctx: ApplicationContext):
        """
        Shows the tickets for each role.

        """

        if len(self.cache["tickets"]) == 0:
            embed = Embed(
                title="Error", description="No tickets were set for any role.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        embed = Embed(title="Role tickets", colour=Colour.blue())

        description = ""
        for role_id in self.cache["tickets"]:
            description += f"{(await self.guild._fetch_role(int(role_id))).mention}: {self.cache['tickets'][role_id]}\n"

        embed.description = description

        await ctx.respond(embed=embed)

    @_tc.command(name="set", description="Sets the tickets amount for a role.")
    @checks.has_permissions(PermissionLevel.EVENT_ADMIN)
    async def _tc_set(self, ctx: ApplicationContext, role: discord.Option(discord.Role, "The roles you want to change the tickets amount for."),
                      tickets: discord.Option(int, "The tickets amount.", min_value=0)):
        """
        Sets the tickets amount for a role in the database.

        """

        if role.id not in self.bot.config["levelRoles"]:
            embed = Embed(
                title="Error", description="Role not found in the database.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        self.cache["tickets"].update({str(role.id): tickets})

        await self.update_db()

        embed = Embed(
            title="Success", description=f"New tickets amount set for {role.mention}.", colour=Colour.green())
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Giveaway(bot))
