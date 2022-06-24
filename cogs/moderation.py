import os
import discord
from discord.ext import commands
from discord import ApplicationContext, Colour, Interaction, Permissions
from discord.ui import View, Select

from datetime import datetime, timezone

from core.context import ModContext
import copy
import re
from core.base_cog import BaseCog

from core.time import TimeConverter, InvalidTime
from core import checks
from core.checks import PermissionLevel

import random


class Moderation(BaseCog):
    _id = "moderation"

    default_cache = {
        "muteRole": None,
        "bans": {  # stores member who is banned, who banned, and reason for ban

        },
        "unbans": {  # stores unban log and who unbanned member

        },
        "kicks": {  # stores member who is kicked, who kicked, and reason for kick

        },
        "mutes": {

        },
        "unmutes": {

        },
        "warns": {  # stores member who is warns, who warned, warning id, and warning

        },
        "pardons": {  # stores pardoned warns

        },
        "notes": {  # stores member, who noted, note id, and note

        },
        "unbanQueue": {  # stores members who need to be unbanned and what time to unban

        },
        "unmuteQueue": {

        }
    }

    async def after_load(self):
        for key, value in list(self.cache["unbanQueue"].items()):
            await self._unban(key, value)

        for key, value in list(self.cache["unmuteQueue"].items()):
            await self._unmute(key, value)

    # @discord.default_permissions(ban_members=True)

    async def get_member_ids(self, ids):
        """
        Gets the IDs of members.

        """

        regex = r"\d{18}"

        return re.findall(regex, ids)

#----------------------------------------ban and unbans----------------------------------------#

    @commands.slash_command(name="ban", description="Bans a member", default_member_permissions=Permissions(ban_members=True))
    @commands.max_concurrency(1, wait=True)
    @checks.has_permissions(PermissionLevel.MOD)
    async def ban(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to ban."),
                  duration: discord.Option(str, description="The duration of the ban.", default="inf"),
                  reason: discord.Option(str, description="Reason for ban.", default="No reason given.")):
        """
        Bans a member via /ban [members] [duration: Optional] [reason: Optional]

        """

        after = None
        if duration != "inf":
            try:
                after = TimeConverter(duration)

            except InvalidTime as e:
                embed = discord.Embed(
                    title="Error", description=e, colour=Colour.red())
                await ctx.respond(embed=embed)

                return

        member_ids = await self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        description = ""
        for member_id in member_ids:
            member = await self.guild.fetch_member(int(member_id))

            if member == None:
                description += f"The member with ID `{member_id}` was not found.\n"
                continue

            if str(ctx.author.id) not in self.bot.config["owners"] and ctx.author.roles[-1] < member.roles[-1]:
                description += f"You do not have the permission to ban the member {member.mention}.\n"
                continue
            
            addition = ""

            try:
                await member.send(f"You have been banned from {self.guild.name}. Reason: {reason}")
                addition = "and a message has been sent.\n"
            except:
                self.logger.error(f"Could not message {member.name}.")
                addition = "but a message could not be sent.\n"

            try:
                await member.ban(reason=reason)
                description += f"The member {member.mention} `{member.name}#{member.discriminator}` has been successfully banned, "
            except Exception as e:
                description += f"The member {member.mention} `{member.name}#{member.discriminator}` could not be banned.\n"
                continue
            
            description+= addition

            if after:
                self.cache["unbanQueue"][str(
                    member_id)] = after.final.timestamp()
                await self._unban(member_id, after.final.timestamp())

            self.cache["bans"].setdefault(str(member_id), []).append(
                {"responsible": ctx.author.id, "reason": reason, "duration": duration, "time": datetime.now().timestamp()})

            self.bot.dispatch("member_delete", ModContext(member=member, moderator=ctx.author,
                              reason=reason, timestamp=datetime.now().timestamp(), duration=duration))

        await self.update_db()

        if after:
            description += f"\nUnbanning at <t:{round(after.final.timestamp())}:F>.\n"

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="unban", description="Unbans a member", default_member_permissions=Permissions(ban_members=True))
    @commands.max_concurrency(1, wait=True)
    @checks.has_permissions(PermissionLevel.MOD)
    async def unban(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to unban."),
                    reason: discord.Option(str, description="Reason for unban.", default="No reason given.")):
        """
        Unbans a member via /unban [members] 

        """

        member_ids = await self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        description = ""
        for member_id in member_ids:
            member = await self.bot.fetch_user(int(member_id))

            if member == None:
                description += f"The member with ID `{member_id}` was not found.\n"
                continue

            try:
                await self.guild.unban(member, reason=reason)
                description += f"The member {member.mention} `{member.name}#{member.discriminator}` has been successfully unbanned."

                try:
                    self.cache["unbanQueue"].pop(member_id)
                except KeyError:
                    pass
            except Exception as e:
                description += f"The member {member.mention} `{member.name}#{member.discriminator}` could not be unbanned.\n"
                continue

            self.cache["unbans"].setdefault(str(member_id), []).append(
                {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp()})

            self.bot.dispatch("member_undelete", ModContext(
                member=member, moderator=ctx.author, reason=reason, timestamp=datetime.now().timestamp()))

        await self.update_db()

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

    async def _unban(self, member, time):
        """
        Handles unban logic depending on time left.

        """
        end = datetime.fromtimestamp(int(time))
        now = datetime.now()
        closetime = (end - now).total_seconds() if time else 0

        if closetime > 0:
            self.bot.loop.call_later(closetime, self._unban_after, member)
        else:
            await self._unban_helper(member)

    def _unban_after(self, member):
        return self.bot.loop.create_task(self._unban_helper(member))

    async def _unban_helper(self, member_id):
        try:
            member = await self.bot.fetch_user(member_id)

            await self.guild.unban(member)

            self.cache["unbans"].setdefault(str(member_id), []).append(
                {"responsible": self.bot.user.id, "reason": "Automated unban", "time": datetime.now().timestamp()})
        except Exception as e:
            self.logger.error(f"{e}")

        self.cache["unbanQueue"].pop(member_id)
        await self.update_db()

    @commands.slash_command(name="bans", description="Lists all bans and unbans for a member.", default_member_permissions=Permissions(manage_messages=True))
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def bans(self, ctx: ApplicationContext, member: discord.Option(discord.Member, description="The members you want to get bans.")):
        """
        Lists all the bans and unbans for a member

        """

        member_id = str(member.id)

        if member_id not in self.cache["bans"]:
            embed = discord.Embed(
                title=f"{member.name}#{member.discriminator} ({member.id})", description="This user has not been banned.", colour=Colour.red())
            await ctx.respond(embed=embed)
            return

        actions = copy.deepcopy(self.cache["bans"][member_id])
        if member_id in self.cache["unbans"]:
            actions.extend(self.cache["unbans"][member_id])

        actions = sorted(actions, key=lambda d: d['time'])

        description = ""
        for action in actions:
            if "duration" in action:
                moderator = await self.bot.fetch_user(action["responsible"])
                description += f'**Ban**\n Moderator: {moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Duration: {action["duration"]} \n Date: <t:{round(action["time"])}:F> \n\n'
            else:
                moderator = await self.bot.fetch_user(action["responsible"])
                description += f'**Unban**\n Moderator: {moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Date: <t:{round(action["time"])}:F> \n\n'

        if not description:
            description = "This user has not been banned."

        embed = discord.Embed(
            title=f"{member.name} ({member.id})", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)


#----------------------------------------kicks----------------------------------------#


    @commands.slash_command(name="kick", description="Kicks a member", default_member_permissions=Permissions(kick_members=True))
    @commands.max_concurrency(1, wait=True)
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def kick(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to kick."),
                   reason: discord.Option(str, description="Reason for kick.", default="No reason given.")):
        """
        Kicks a member via /kick [members] [reason: Optional]

        """

        member_ids = await self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        description = ""
        for member_id in member_ids:
            member = await self.guild.fetch_member(int(member_id))

            if member == None:
                description += f"The member with ID `{member_id}` was not found.\n"
                continue

            if str(ctx.author.id) not in self.bot.config["owners"] and ctx.author.roles[-1] < member.roles[-1]:
                description += f"You do not have the permission to kick the member {member.mention}.\n"
                continue

            addition = ""

            try:
                await member.send(f"You have been kicked from {self.guild.name}. Reason: {reason}")
                addition = "and a message has been sent.\n"
            except:
                self.logger.error(f"Could not message {member.name}.")
                addition = "but a message could not be sent.\n"

            try:
                await member.kick(reason=reason)
                description += f"The member {member.mention} `{member.name}#{member.discriminator}` has been successfully kicked, "
            except Exception as e:
                description += f"The member {member.mention} `{member.name}#{member.discriminator}` could not be kicked.\n"
                continue

            description += addition
            
            self.cache["kicks"].setdefault(str(member_id), []).append(
                {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp()})

            self.bot.dispatch("member_kick", ModContext(member=member, moderator=ctx.author,
                              reason=reason, timestamp=datetime.now().timestamp()))

        await self.update_db()

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="kicks", description="Lists all kicks for a member.", default_member_permissions=Permissions(manage_messages=True))
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def kicks(self, ctx: ApplicationContext, member: discord.Option(discord.Member, description="The members you want to get bans.")):
        """
        Lists all the kicks for a member.

        """

        member_id = str(member.id)

        if member_id not in self.cache["kicks"]:
            embed = discord.Embed(
                title=f"{member.name} ({member.id})", description="This user has not been kicked.", colour=Colour.red())
            await ctx.respond(embed=embed)
            return

        actions = copy.deepcopy(self.cache["kicks"][member_id])
        actions = sorted(actions, key=lambda d: d['time'])

        description = ""
        for action in actions:
            moderator = await self.bot.fetch_user(action["responsible"])
            description += f'**Kick**\n Moderator: {moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Date: <t:{round(action["time"])}:F> \n\n'

        if not description:
            description = "This user not been kicked."

        embed = discord.Embed(
            title=f"{member.name} ({member.id})", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

#----------------------------------------Mute and Unmute----------------------------------------#

    @commands.slash_command(name="setmute", description="Sets the mute role.", default_member_permissions=Permissions(manage_channels=True))
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def setmute(self, ctx: ApplicationContext, role: discord.Option(discord.Role, description="mute role")):
        """
        Sets the mute role via /mute [role]

        """

        if await self.guild._fetch_role(role.id) == None:
            embed = discord.Embed(
                title="Success", description=f"Role was not found in the guild.", colour=Colour.green())
            await ctx.respond(embed=embed)

            return

        self.cache["muteRole"] = role.id
        await self.update_db()

        embed = discord.Embed(
            title="Success", description=f"Successfully set the mute role as {role.mention}", colour=Colour.green())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="mute", description="Mutes a member", default_member_permissions=Permissions(manage_messages=True))
    @commands.max_concurrency(1, wait=True)
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def mute(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to mute."),
                   duration: discord.Option(str, description="The duration of the mute.", default="inf"),
                   reason: discord.Option(str, description="Reason for mute.", default="No reason given.")):
        """
        Mutes a member via /mute [members] [duration: Optional] [reason: Optional]

        """

        if not self.cache["muteRole"]:
            embed = discord.Embed(
                title="Error", description="Please set a mute role first by running `/setmute [role]`", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        after = None
        if duration != "inf":
            try:
                after = TimeConverter(duration)

            except InvalidTime as e:
                embed = discord.Embed(
                    title="Error", description=e, colour=Colour.red())
                await ctx.respond(embed=embed)

                return

        member_ids = await self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        mute_role = await self.guild._fetch_role(self.cache["muteRole"])

        description = ""
        for member_id in member_ids:
            member: discord.Member = await self.guild.fetch_member(int(member_id))

            if member == None:
                description += f"The member with ID `{member_id}` was not found.\n"
                continue

            if str(ctx.author.id) not in self.bot.config["owners"] and ctx.author.roles[-1] < member.roles[-1]:
                description += f"You do not have the permission to mute the member {member.mention}.\n"
                continue

            if mute_role in member.roles:
                description += f"The member with ID `{member_id}` is already muted.\n"
                continue

            try:
                roles = [role.id for role in member.roles]
                await member.edit(roles=[mute_role])

                description += f"The member {member.mention} `{member.name}#{member.discriminator}` has been successfully muted, "
            except Exception as e:
                self.bot.dispatch("error", e)
                description += f"The member {member.mention} `{member.name}#{member.discriminator}` could not be muted.\n"

                continue

            try:
                dm = await member.create_dm()
                await dm.send(f"You have been muted in {self.guild.name}. Reason: {reason}")
                description += "and a message has been sent.\n"
            except:
                self.logger.error(f"Could not message {member.name}.")
                description += "but a message could not be sent.\n"

            if after:
                self.cache["unmuteQueue"][str(
                    member_id)] = after.final.timestamp()
                await self._unmute(member_id, after.final.timestamp())

            self.cache["mutes"].setdefault(str(member_id), []).append(
                {"responsible": ctx.author.id, "reason": reason, "duration": duration, "time": datetime.now().timestamp(), "roles": roles})

            self.bot.dispatch("member_mute", ModContext(member=member, moderator=ctx.author,
                              reason=reason, timestamp=datetime.now().timestamp(), duration=duration))

        await self.update_db()

        if after:
            description += f"Unmuting at <t:{round(after.final.timestamp())}:F>.\n"

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="unmute", description="Unmutes a member.", default_member_permissions=Permissions(manage_messages=True))
    @commands.max_concurrency(1, wait=True)
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def unmute(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to unmute."),
                     reason: discord.Option(str, description="Reason for unmute.", default="No reason given.")):
        """
        Unmutes a member via /unmute [members] [reason: optional]

        """

        member_ids = await self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.")
            await ctx.respond(embed=embed)

            return

        mute_role = await self.guild._fetch_role(self.cache["muteRole"])

        description = ""
        for member_id in member_ids:
            member: discord.Member = await self.guild.fetch_member(int(member_id))

            if member == None:
                description += f"The member with ID `{member_id}` was not found.\n"
                continue

            if mute_role not in member.roles:
                description += f"The member with ID `{member_id}` is not muted.\n"
                continue

            try:
                roles = [await self.guild._fetch_role(role_id) for role_id in self.cache["mutes"][member_id][-1]["roles"]]
                await member.edit(roles=roles)

                description += f"The member {member.mention} `{member.name}#{member.discriminator}` has been successfully unmuted."

                try:
                    self.cache["unmuteQueue"].pop(member_id)
                except KeyError:
                    pass
            except Exception as e:
                description += f"The member {member.mention} `{member.name}#{member.discriminator}` could not be unmuted.\n"
                continue

            self.cache["unmutes"].setdefault(str(member_id), []).append(
                {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp()})

            self.bot.dispatch("member_unmute", ModContext(
                member=member, moderator=ctx.author, reason=reason, timestamp=datetime.now().timestamp()))

        await self.update_db()

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

    async def _unmute(self, member, time):
        """
        Handles unmute logic depending on time left.

        """
        end = datetime.fromtimestamp(int(time))
        now = datetime.now()
        closetime = (end - now).total_seconds() if time else 0

        if closetime > 0:
            self.bot.loop.call_later(closetime, self._unmute_after, member)
        else:
            await self._unmute_helper(member)

    def _unmute_after(self, member):
        return self.bot.loop.create_task(self._unmute_helper(member))

    async def _unmute_helper(self, member_id):
        try:
            member = await self.guild.fetch_member(int(member_id))
            roles = [await self.guild._fetch_role(
                role_id) for role_id in self.cache["mutes"][member_id][-1]["roles"]]

            await member.edit(roles=roles)

            self.cache["unmutes"].setdefault(str(member_id), []).append(
                {"responsible": self.bot.user.id, "reason": f"Automated unmute", "time": datetime.now().timestamp()})
        except Exception as e:
            self.logger.error(f"{e}")

        self.cache["unmuteQueue"].pop(member_id)
        await self.update_db()

    @commands.slash_command(name="mutes", description="Lists all mutes and unmutes for a member.", default_member_permissions=Permissions(manage_messages=True))
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def mutes(self, ctx: ApplicationContext, member: discord.Option(discord.Member, description="The members you want to get mute history.")):
        """
        Lists all the mutes and unmutes for a member

        """

        member_id = str(member.id)

        if member_id not in self.cache["mutes"]:
            embed = discord.Embed(
                title=f"{member.name} ({member.id})", description="This user has not been muted.", colour=Colour.red())
            await ctx.respond(embed=embed)
            return

        actions = copy.deepcopy(self.cache["mutes"][member_id])
        if member_id in self.cache["unmutes"]:
            actions.extend(self.cache["unmutes"][member_id])

        actions = sorted(actions, key=lambda d: d['time'])

        description = ""
        for action in actions:
            if "duration" in action:
                moderator = await self.bot.fetch_user(action["responsible"])
                description += f'**Mute**\n Moderator: {moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Duration: {action["duration"]} \n Date: <t:{round(action["time"])}:F> \n\n'
            else:
                moderator = await self.bot.fetch_user(action["responsible"])
                description += f'**Unmute**\n Moderator: {moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Date: <t:{round(action["time"])}:F> \n\n'

        if not description:
            description = "This user has not been muted."

        embed = discord.Embed(
            title=f"{member.name} ({member.id})", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

#----------------------------------------Warn----------------------------------------#

    @commands.slash_command(name="warn", description="Warns a member.", default_member_permissions=Permissions(manage_messages=True))
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def warn(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to warn."),
                   reason: discord.Option(str, description="Warn reason.", default="No reason given.")):
        """
        Warns a member via /warn [members] [reason]

        """

        member_ids = await self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        description = ""
        for member_id in member_ids:
            member: discord.Member = await self.bot.fetch_user(int(member_id))

            if member == None:
                description += f"The member with ID `{member_id}` was not found.\n"
                continue

            description += f"The member {member.mention} `{member.name}#{member.discriminator}` has been successfully warned, "

            try:
                await member.send(f"You have been warned in {self.guild.name}. Reason: {reason}")
                description += "and a message has been sent.\n"
            except:
                self.logger.error(f"Could not message {member.name}.")
                description += "but a message could not be sent.\n"

            self.cache["warns"].setdefault(str(member_id), []).append(
                {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp()})

            self.bot.dispatch("member_warn", ModContext(member=member, moderator=ctx.author,
                              reason=reason, timestamp=datetime.now().timestamp()))

        await self.update_db()

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="pardon", description="Pardons a warn", default_member_permissions=Permissions(manage_messages=True))
    @commands.max_concurrency(1, wait=True)
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def pardon(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to pardon warns for."),
                     reason: discord.Option(str, description="Warn reason.", default="No reason given.")):
        """
        Pardons warns for some members via /pardon [members]

        """

        member_ids = await self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        async def _warns_callback(interaction: Interaction):
            warn_select.values.sort(reverse=True)
            for value in warn_select.values:
                self.cache["pardons"].setdefault(str(member_id), []).append(
                    {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp(), "warn": self.cache["warns"][str(member_id)][int(value)]})

                self.cache["warns"][str(member_id)].pop(int(value))

            self.bot.dispatch("member_pardon", ModContext(
                member=member, moderator=ctx.author, reason=reason, timestamp=datetime.now().timestamp()))

            await interaction.response.defer()

            warn_view.stop()

        embed = discord.Embed(
            title="Warns", description="Fetching warns...", colour=Colour.blue())
        await ctx.respond(embed=embed)

        for member_id in member_ids:
            member: discord.User = await self.bot.fetch_user(int(member_id))

            if member == None or len(self.cache["warns"][str(member_id)]) == 0:
                continue

            warn_select = Select(placeholder="Select warns", max_values=len(self.cache["warns"][str(member_id)]),
                                 options=[discord.SelectOption(label=str(count+1), value=str(count)) for count in range(len(self.cache["warns"][str(member_id)]))])
            warn_select.callback = _warns_callback

            warn_view = View(warn_select)

            embed.description = f"**{member.name}#{member.discriminator}**\n"
            embed.description += "".join([f"Responsible: <@{warn['responsible']}> Reason: {warn['reason'] if not '' else 'No reason given'}\n\n"
                                          for warn in self.cache["warns"][str(member_id)]])

            await ctx.interaction.edit_original_message(embed=embed, view=warn_view)

            await warn_view.wait()

        await self.update_db()

        await ctx.delete()

    @commands.slash_command(name="warns", description="Lists all warns for a member.", default_member_permissions=Permissions(manage_messages=True))
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def warns(self, ctx: ApplicationContext, member: discord.Option(discord.Member, description="The members you want to get warns for.")):
        """
        Lists all the warns for a member

        """

        member_id = str(member.id)

        if member_id not in self.cache["warns"]:
            embed = discord.Embed(
                title=f"{member.name} ({member.id})", description="This user has no warns", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        actions = copy.deepcopy(self.cache["warns"][member_id])
        if member_id in self.cache["pardons"]:
            actions.extend(self.cache["pardons"][member_id])

        actions = sorted(actions, key=lambda d: d["time"])

        description = ""
        for action in actions:
            if "warn" in action:
                description += "**Pardon**\n"
            else:
                description += "**Warn**\n"

            moderator = await self.bot.fetch_user(action["responsible"])
            description += f"Moderator: {moderator.mention} ({action['responsible']}) \n Reason: {action['reason']} \n Date: <t:{round(action['time'])}:F>\n"

            if "warn" in action:
                moderator = await self.bot.fetch_user(action["warn"]["responsible"])
                description += f"**Pardoned warn**\nModerator: {moderator.mention} ({action['warn']['responsible']}) \n Reason: {action['warn']['reason']} \n Date: <t:{round(action['warn']['time'])}:F>\n"

            description += "\n"

        if not description:
            description = "This user has no warns."

        embed = discord.Embed(
            title=f"{member.name} ({member.id})", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

#----------------------------------------Note----------------------------------------#

    @commands.slash_command(name="note", description="Write a note about a member", default_member_permissions=Permissions(manage_messages=True))
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def note(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to write a note about."),
                   note: discord.Option(str, description="Note")):
        """
        Writes a note about a member member via /note [members] [note]

        """

        member_ids = await self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        description = ""
        for member_id in member_ids:
            member: discord.Member = await self.bot.fetch_user(int(member_id))

            if member == None:
                description += f"The member with ID `{member_id}` was not found.\n"
                continue

            description += f"The member {member.mention} `{member.name}#{member.discriminator}` got a note written about them.\n"

            self.cache["notes"].setdefault(str(member_id), []).append(
                {"responsible": ctx.author.id, "note": note, "time": datetime.now().timestamp()})

        await self.update_db()

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="omit", description="Deletes a note", default_member_permissions=Permissions(manage_messages=True))
    @commands.max_concurrency(1, wait=True)
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def remove_note(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to omit notes for.")):
        """
        Omits notes for some members via /omit [members]

        """

        member_ids = await self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        async def _notes_callback(interaction: Interaction):
            note_select.values.sort(reverse=True)
            for value in note_select.values:
                self.cache["notes"][str(member_id)].pop(int(value))

            await interaction.response.defer()

            note_view.stop()

        embed = discord.Embed(
            title="Notes", description="Fetching notes...", colour=Colour.blue())
        await ctx.respond(embed=embed)

        for member_id in member_ids:
            member: discord.User = await self.bot.fetch_user(int(member_id))

            if member == None or len(self.cache["notes"][str(member_id)]) == 0:
                continue

            note_select = Select(placeholder="Select notes", max_values=len(self.cache["notes"][str(member_id)]),
                                 options=[discord.SelectOption(label=str(count+1), value=str(count)) for count in range(len(self.cache["notes"][str(member_id)]))])
            note_select.callback = _notes_callback

            note_view = View(note_select)

            embed.description = f"**{member.name}#{member.discriminator}**\n"
            embed.description += "".join([f"Responsible: <@{note['responsible']}> Note: {note['note']}\n\n"
                                          for note in self.cache["notes"][str(member_id)]])

            await ctx.interaction.edit_original_message(embed=embed, view=note_view)

            await note_view.wait()

        await self.update_db()

        await ctx.delete()

    @commands.slash_command(name="notes", description="Lists all notes for a member", default_member_permissions=Permissions(manage_messages=True))
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def notes(self, ctx: ApplicationContext, member: discord.Option(discord.Member, description="The members you want to get notes.")):
        """
        Lists all the notes for a member

        """

        member_id = str(member.id)

        if member_id not in self.cache["notes"]:
            embed = discord.Embed(
                title=f"{member.name} ({member.id})", description="This user has no notes", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        actions = copy.deepcopy(self.cache["notes"][member_id])
        actions = sorted(actions, key=lambda d: d['time'])

        description = ""
        for action in actions:
            moderator = await self.bot.fetch_user(action["responsible"])
            description += f'Moderator: {moderator.mention} ({action["responsible"]}) \n Note: {action["note"]} \n Date: <t:{round(action["time"])}:F> \n\n'

        if not description:
            description = "This user has no notes."

        embed = discord.Embed(
            title=f"{member.name} ({member.id})", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

#--------------------------------------------------------------------------------#

    @commands.slash_command(name="slowmode", description="Sets slowmode for a channel.", default_member_permissions=Permissions(manage_channels=True))
    @checks.has_permissions(PermissionLevel.MOD)
    async def slowmode(self, ctx: ApplicationContext, duration: discord.Option(str, description="The duration of the slowmode."),
                       channel: discord.Option(discord.TextChannel, description="The channel you want to set slowmode.", default=None)):
        """
        Sets slowmode for a channel.

        """
        regex = (r'((?P<hours>-?\d+)h)?'
                 r'((?P<minutes>-?\d+)m)?'
                 r'((?P<seconds>-?\d+)s)?')
        match = re.compile(regex, re.IGNORECASE).match(str(duration))

        seconds = None

        if match:
            for k, v in match.groupdict().items():
                if v:
                    if not seconds:
                        seconds = 0

                    if k == "hours":
                        seconds += int(v) * 3600
                    elif k == "minutes":
                        seconds += int(v) * 60
                    elif k == "seconds":
                        seconds += int(v)

        if seconds is None:
            embed = discord.Embed(
                title="Error", description=f"Could not parse duration: {duration}. Make sure it is in the form []h[]m[]s.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        if duration > 21600:
            embed = discord.Embed(
                title="Error", description=f"Duration {seconds}s too large. Maximum slowmode is 6h (21600s).", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        if not channel:
            channel = ctx.channel

        await channel.edit(slowmode_delay=duration)

        embed = discord.Embed(
            title="Success", description=f"Successfully set slowmode in {channel.mention} to {duration}s.", colour=Colour.green())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="purge", description="Purge messages.", default_member_permissions=Permissions(manage_messages=True))
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def purge(self, ctx: ApplicationContext, messages: discord.Option(int, description="Number of messages to search through.", min_value=1),
                    user: discord.Option(discord.Member, description="User's messages to purge.", default=None)):
        """
        Purges messages via /purge [number] [user: optional]

        """

        deleted = await ctx.channel.purge(limit=messages,
                                          check=lambda m, user=user: (m.author.id == user.id and not m.pinned) if user else (not m.pinned))  # bruh what is this lambda function

        embed = discord.Embed(
            title="Success", description=f"Successfully purged {len(deleted)} messages.", colour=Colour.green())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="bonk", description="Bonk your enemies.", default_member_permissions=Permissions(manage_messages=True))
    @checks.has_permissions(PermissionLevel.STAFF)
    async def bonk(self, ctx: ApplicationContext, member: discord.Option(discord.Member, "Member to bonk.")):
        """
        Bonks user, bonk owner for a surprise.

        """

        await ctx.defer()

        if member.id == 227244423166033921:
            file = discord.File("./assets/wake-up-luma.gif")
            await ctx.respond(member.mention, file=file)

            return

        file = discord.File(
            f"./assets/bonk/{random.choice(os.listdir('./assets/bonk/'))}")

        await ctx.respond(":(" if member.id == 906318377432281088 else member.mention, file=file)



def setup(bot):
    bot.add_cog(Moderation(bot))
