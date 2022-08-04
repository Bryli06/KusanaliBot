import copy
import random
import re

import discord
from discord.ext import commands
from discord.ui import Select, Button, View

from discord import ApplicationContext, Colour, Embed, Interaction, Permissions, SlashCommandGroup, TextChannel, OptionChoice

from core import checks
from core.time import TimeConverter, InvalidTime
from core.base_cog import BaseCog
from core.checks import PermissionLevel

from datetime import datetime

from copy import deepcopy


class Giveaway(BaseCog):
    _id = "giveaway"

    default_cache = {}

    async def load_cache(self): #each countdown gets its own document
        cursor = self.db.find({ })
        docs = await cursor.to_list(length=10) #how many documents to buffer shouldn't be too high
        while docs:
            for document in docs:
                _id = document.pop("_id")
                self.cache[_id] = document

            docs = await cursor.to_list(length=10)
        
        self.guild: discord.Guild = await self.bot.fetch_guild(self.bot.config["guild_id"])
        
        self.bot.tasks_done = self.bot.tasks_done + 1


    async def update_db(self, _id): #we need a different insert command that allows us to insert into seperate documents
        if _id not in self.cache:
            await self.db.delete_one({"_id": _id})
            return

        await self.db.find_one_and_update(
            {"_id": _id},
            {"$set": self.cache[_id]},
            upsert=True,
        )

    _ga = SlashCommandGroup("giveaway", "Contains all giveaway commands.",
                            default_member_permissions=Permissions(manage_messages=True))

    async def after_load(self):
        self.loop_cache = {}
        await self.start_countdowns()

    async def start_countdowns(self):
        """
        Starts all giveaway countdowns. Used when the bot goes online.

        """

        # copied to avoid exceptions from removing done giveaways while iterating
        for message_id in list(self.cache.keys()):
            if not self.cache[int(message_id)]["ended"]:
                await self.start_countdown(int(message_id))

    async def start_countdown(self, message_id):
        """
        Starts a giveaway countdown given the giveaway ID taken from the message of the giveaway.

        """

        # get the channel the giveaway is in
        channel: TextChannel = await self.guild.fetch_channel(
            self.cache[message_id]["channel"])

        # try fetching the message
        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            self.bot.dispatch("error", e,
                              f"There seems to be an active giveaway in {channel.mention} that the bot cannot access.",
                              f"Delete the giveaway in {channel.mention} manually `ID: {message_id}`.")

            self.cache.pop(message_id)
            await self.update_db(message_id)

            return

        # update the button, otherwise it won't work
        await self.add_enter_button(message)

        # get time remaining in computer time
        unix = self.cache[message_id]["unixEndTime"] - datetime.now().timestamp()

        # add task to close giveaway after countdown has finished
        self.loop_cache[message_id] = self.bot.loop.call_later(unix, self.giveaway_end, message)

    async def add_enter_button(self, message: discord.Message):
        """
        Adds an enter button for giveaways.

        """

        async def _enter_callback(interaction: Interaction):
            giveaway = self.cache[message.id]

            roles = []
            for role in interaction.user.roles[1:]:
                roles.append(role.id)


            # stops if user has already joined giveaway
            if str(interaction.user.id) in giveaway["participants"]:
                embed = discord.Embed(
                    title="Error", description="You can't enter more than once.", colour=Colour.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

                return
            

            if set(roles) & set(giveaway["bannedRoles"]):
                embed = discord.Embed(
                    title="Error", description="You possess a banned role.", colour=Colour.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            # stops if user does not have any of the roles needed to enter
            if not (set(roles) & set(giveaway["requiredRoles"])) and giveaway["requiredRoles"]:
                embed = discord.Embed(
                    title="Error", description="You do not possess any of the required roles needed to enter.", colour=Colour.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

                
            # adds user to the participants list
            giveaway["participants"][str(interaction.user.id)] = roles
            await self.update_db(message.id)

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

        if not message or message.id not in self.cache:
            return

        giveaway = self.cache[message.id]

        winners = giveaway["winners"]
        required_roles = giveaway["requiredRoles"]
        banned_roles = giveaway["bannedRoles"]
        participants = giveaway["participants"]
        tickets = giveaway["tickets"]
        reward = giveaway["reward"]
        
        participant_ids = []
        participant_weights = []

        for member_id, roles in list(participants.items()):
            if (not (set(roles) & set(required_roles)) and required_roles) or set(roles) & set(banned_roles):
                continue
            
            roles_with_tickets = set(map(int, tickets.keys())) & set(roles)

            weight = 1

            for ticket in roles_with_tickets:
                weight += tickets[str(ticket)]

            participant_weights.append(weight)
            participant_ids.append(member_id)
        
        # end giveaway with no winners
        if len(participant_ids) == 0:
            embed = discord.Embed(
                title="Giveaway has ended!", description="The giveaway has ended with no winners.", colour=Colour.blue())

            await message.edit(embed=embed, view=None)

            self.cache.pop(message.id)
            await self.update_db(message.id)

            return

        winner_ids = []
        winner_weights = []

        # all participants win if the number of winners is greater than the number of participants
        if winners >= len(participant_ids):
            winner_ids = participant_ids
            winner_weights = participant_weights
            
            participant_ids = []
            participant_weights = []
        else:
            for i in range(winners):
                winner_id = random.choices(participant_ids, participant_weights)[0]

                index = participant_ids.index(winner_id)

                winner_ids.append(participant_ids.pop(index))
                winner_weights.append(participant_weights.pop(index))

        
        giveaway["participant_weights"] = participant_weights
        giveaway["participant_ids"] = participant_ids

        giveaway["winner_weights"] = winner_weights
        giveaway["winner_ids"] = winner_ids


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

        self.cache[message.id]["ended"] = True
        await self.update_db(message.id)
        
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot:
            return

        if before.roles == after.roles:
            return
        
        for _id, giveaway in self.cache.items():
            if not giveaway["ended"] and str(before.id) in giveaway["participants"]:
                role_id = []
                for role in after.roles[1:]:
                    role_id.append(role.id)
                giveaway["participants"][str(before.id)] = role_id


    @_ga.command(name="end", description="Ends a giveaway")
    @checks.has_permissions(PermissionLevel.EVENT_ADMIN)
    async def message_giveaway_end(self, ctx: ApplicationContext, message_id: discord.Option(str, "Message id of the giveaway to end early")):
        """
        End a giveaway before its time.

        """
        message_id = int(message_id)
        # stop if the message is not a giveaway
        if message_id not in self.cache:
            embed = discord.Embed(
                title="Error", description="Message is not an active giveaway.")
            await ctx.respond(embed=embed, ephemeral=True)

            return
        
        channel: TextChannel = await self.guild.fetch_channel(
            self.cache[message_id]["channel"])
        
        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            self.bot.dispatch("error", e,
                              f"There seems to be an active giveaway in {channel.mention} that the bot cannot access.",
                              f"Delete the giveaway in {channel.mention} manually `ID: {message_id}`.")

            self.cache.pop(message_id)
            await self.update_db(message_id)

            return

        self.giveaway_end(message)

        embed = discord.Embed(
            title="Success", description="Giveaway was ended.", colour=Colour.green())
        await ctx.respond(embed=embed, ephemeral=True)



    @_ga.command(name="edit", description="Edits a giveaway")
    @checks.has_permissions(PermissionLevel.EVENT_ADMIN)
    async def giveaway_edit(self, ctx: ApplicationContext, message_id: discord.Option(str, "message id of the giveaway to end early."), 
            field: discord.Option(int, "The field you want to edit", choices=[OptionChoice("Reward", 0), 
                OptionChoice("Winners", 1), OptionChoice("End", 2), OptionChoice("Required Roles", 3),
                OptionChoice("Banned Roles", 4), OptionChoice("Tickets", 5)]), value: discord.Option(str, "Value to change to.", default="")):

        await ctx.defer()

        message_id = int(message_id)
        # stop if the message is not a giveaway
        if message_id not in self.cache:
            embed = discord.Embed(
                title="Error", description="Message is not an active giveaway.")
            await ctx.respond(embed=embed, ephemeral=True)

            return

        giveaway = self.cache[message_id]
        
        channel: TextChannel = await self.guild.fetch_channel(
            giveaway["channel"])
        
        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            self.bot.dispatch("error", e,
                              f"There seems to be an active giveaway in {channel.mention} that the bot cannot access.",
                              f"Delete the giveaway in {channel.mention} manually `ID: {message_id}`.")

            self.cache.pop(message_id)
            await self.update_db(message_id)

            return

        embed = message.embeds[0] 

        if field == 0: #reward
            giveaway["reward"] = value
            await self.update_db(message_id)

            embed.title = f"{value} giveaway!"

            await message.edit(embed=embed)

        elif field == 1:
            giveaway["winners"] = int(value)
            await self.update_db(message_id)

            embed.description = f"A giveaway has started and will end on <t:{giveaway['unixEndTime']}:F>!\n{giveaway['winners']} participant{'s' if giveaway['winners'] > 1 else ''} will be selected at the end."

            await message.edit(embed=embed)

        elif field == 2:
            duration = 0
            try:
                duration = TimeConverter(value)

            except InvalidTime as e:
                embed = discord.Embed(
                    title="error", description=e, colour=Colour.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return

            # stop if amount is 0
            if duration == 0:
                embed = discord.Embed(
                    title=f"Error", description="Time cannot be 0.", colour=Colour.red())
                ctx.respond(embed=embed)

                return
            
            giveaway["unixEndTime"] = int(duration.final.timestamp())
            await self.update_db(message_id)

            embed.description = f"A giveaway has started and will end on <t:{giveaway['unixEndTime']}:F>!\n{giveaway['winners']} participant{'s' if giveaway['winners'] > 1 else ''} will be selected at the end."

            await message.edit(embed=embed)

            self.loop_cache[message_id].cancel()

            unix = self.cache[message_id]["unixEndTime"] - datetime.now().timestamp()

            self.loop_cache[message_id] = self.bot.loop.call_later(unix, self.giveaway_end, message)

        elif field == 3:
            description = ""
            required = await self.parse_roles(value)

            giveaway["requiredRoles"] = required
            await self.update_db(message_id)

            for role in required:
                description += f"<@&{role}>\n"

            for i, f in enumerate(embed.fields):
                if f.name.startswith("Roles allowed"):

                    if description:
                        embed.set_field_at(index=i, name="Roles allowed to participate",value=description)
                    else:
                        embed.remove_field(i)
                    
                    description = None

                    break

            if description:
                embed.add_field(name="Roles allowed to participant", value=description)
            
            await message.edit(embed=embed)


        elif field == 4:
            description = ""
            banned = await self.parse_roles(value)

            giveaway["bannedRoles"] = banned
            await self.update_db(message_id)

            for role in banned:
                description += f"<@&{role}>\n"

            for i, f in enumerate(embed.fields):
                if f.name.startswith("Roles banned"):

                    if description:
                        embed.set_field_at(index=i, name="Roles banned from participating",value=description)
                    else:
                        embed.remove_field(i)
                    
                    description = None

                    break

            if description:
                embed.add_field(name="Roles banned from participating", value=description)
            
            await message.edit(embed=embed)

        elif field == 5:
            description = ""
            weight = await self.parse_tickets(value)

            giveaway["tickets"] = weight
            await self.update_db(message_id)

            for k, v in weight.items():
                description += f"<@&{k}>: {v} ticket{'' if v==1 else 's'}\n"

            for i, f in enumerate(embed.fields):
                if f.name.startswith("Additional"):

                    if description:
                        embed.set_field_at(index=i, name="Additional Role Ticktes",value=description)
                    else:
                        embed.remove_field(i)
                    
                    description = None

                    break

            if description:
                embed.add_field(name="Additional Role Ticktes", value=description)
            
            await message.edit(embed=embed)

        embed = discord.Embed(
            title="Success", description="Giveaway was edited.", colour=Colour.green())
        await ctx.respond(embed=embed, ephemeral=True)
        
            

        


    @_ga.command(name="create", description="Creates a new giveaway")
    @checks.has_permissions(PermissionLevel.EVENT_ADMIN)
    async def _ga_create(self, ctx: ApplicationContext, reward: discord.Option(str, "The name of the reward."),
                         winners: discord.Option(int, "The number of winners.", min_value=1),
                         end: discord.Option(str, "How long is the giveaway."), 
                         required_roles: discord.Option(str, "The required roles", default=""),
                         banned_roles: discord.Option(str, "The roles that are not allowed to join", default=""),
                         tickets: discord.Option(str, "How many tickets to give to roles", default="")):
        """
        Creates a new giveaway.

        """

        await ctx.defer(ephemeral=True)
        
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
        
        required = await self.parse_roles(required_roles)
        banned = await self.parse_roles(banned_roles)
        weights = await self.parse_tickets(tickets)
        embed = discord.Embed(title=f"{reward} giveaway!", description=f"A giveaway has started and will end on <t:{int(duration.final.timestamp())}:F>!\n{winners} participant{'s' if winners > 1 else ''} will be selected at the end.", colour=Colour.blue())

        embed.set_author(name=f"Host: {ctx.author.display_name}", icon_url=ctx.author.display_avatar)

        value = ""
        if required:
            for role in required:
                value += f"<@&{role}>\n"

            embed.add_field(name="Roles allowed to participate", value=value)
        
        if banned:
            value = ""
            for role in banned:
                value += f"<@&{role}>\n"

            embed.add_field(name="Roles banned from participating", value=value)

        if weights:
            value = ""
            for k, v in weights.items():
                value += f"<@&{k}>: {v} ticket{'' if v==1 else 's'}\n"

            embed.add_field(name="Additional Role Ticktes", value=value)
                
        class confirmButton(discord.ui.Button):
            def __init__(self, giveaway):
                self.giveaway = giveaway

                super().__init__(
                    label="✅", 
                    style=discord.ButtonStyle.green
                )

            async def callback(self, interaction: Interaction):
                for child in self.view.children:
                    child.disabled = True
            
                giveaway = {
                    "channel": ctx.channel_id,
                    "unixEndTime": int(duration.final.timestamp()),
                    "reward": reward,
                    "winners": winners,
                    "tickets": weights,
                    "requiredRoles": required,
                    "bannedRoles": banned,
                    "participants": {},
                    "ended": False
                }
            
                message = await ctx.channel.send(embed=embed)

                self.giveaway.cache[message.id] = giveaway
                await self.giveaway.update_db(message.id)

                await self.giveaway.start_countdown(message.id)
            
                await interaction.response.edit_message(view=self.view)

        class denyButton(discord.ui.Button):
            def __init__(self):

                super().__init__(
                    label="❌", 
                    style=discord.ButtonStyle.red
                )
            async def callback(self, interaction: Interaction):
                for child in self.view.children:
                    child.disabled = True

                await interaction.response.edit_message(view=self.view)


        view = View(timeout=60)

        view.add_item(confirmButton(self))
        view.add_item(denyButton())

        await ctx.respond(embed=embed, view=view, ephemeral=True)



    @_ga.command(name="reroll", description="rerolls a giveaway")
    @checks.has_permissions(PermissionLevel.EVENT_ADMIN)
    async def reroll(self, ctx: ApplicationContext, messageid: discord.Option(str, "giveaway to reroll"), amount: discord.Option(int, "Number of new winners", default=1)):
        """
        Ends an active giveaway.
        
        """

        message_id = int(messageid)

        if message_id not in self.cache:
            embed = discord.Embed(
                title="Error", description="Message is not an active giveaway.")
            await ctx.respond(embed=embed, ephemeral=True)

            return

        giveaway = self.cache[message_id]
        
        channel: TextChannel = await self.guild.fetch_channel(
            giveaway["channel"])
        
        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            self.bot.dispatch("error", e,
                              f"There seems to be an active giveaway in {channel.mention} that the bot cannot access.",
                              f"Delete the giveaway in {channel.mention} manually `ID: {message_id}`.")

            self.cache.pop(message_id)
            await self.update_db(message_id)

            return

        giveaway = self.cache[message.id]

        participants = giveaway["participant_weights"]
        participant_ids = giveaway["participant_ids"]

        new_winners = []
        new_ids = []

        # all participants win if the number of winners is greater than the number of participants
        if amount >= len(participant_ids):
            new_ids = participant_ids
            new_winners = participants
            
            participant_ids = []
            participants = []
        else:
            for i in range(amount):
                winner_id = random.choices(participant_ids, participants)[0]

                index = participant_ids.index(winner_id)

                new_ids.append(participant_ids.pop(index))
                new_winners.append(participants.pop(index))

        
        giveaway["participant_weights"] = participants
        giveaway["participant_ids"] = participant_ids

        giveaway["winner_weights"].extend(new_winners)
        giveaway["winner_ids"].extend(new_ids)

        await self.update_db(message_id)
    
        description = "Congratulations to: "
        for winner_id in new_ids:
            description += f"<@{winner_id}> "

        await ctx.respond(description)

    async def parse_roles(self, ids):
        regex = r"\d+"

        return list(map(int, re.findall(regex, ids)))

    async def parse_tickets(self, tickets):
        regex = r"\d+"

        parsed = re.findall(regex, tickets)
        
        weights = {} 

        for i in range(len(parsed)//2):
            weights[parsed[2*i]] = int(parsed[2*i+1])

        return weights
            
    


def setup(bot):
    bot.add_cog(Giveaway(bot))
