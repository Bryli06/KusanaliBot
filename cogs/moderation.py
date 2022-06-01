import discord
from discord.ext import commands
from discord import SlashCommandGroup, ApplicationContext, SlashCommand, default_permissions, option
from discord.commands import Option
from datetime import datetime

import copy
from math import floor
import re
from core.base_cog import BaseCog

from core.time import UserFriendlyTime
from core import checks
from core.checks import PermissionLevel
from core import config


class Moderation(BaseCog):
    _id = "moderation"

    default_cache = {
        "ban": {  # stores member who is banned, who banned, and reason for ban

        },
        "unban": {  # stores unban log and who unbanned member

        },
        "kick": {  # stores member who is kicked, who kicked, and reason for kick

        },
        
        "mute": {

        },
        
        "unmute": {

        },

        "muterole": None,

        "warn": {  # stores member who is warns, who warned, warning id, and warning

        },

        "warnid": 0,

        "pardon": {  # stores pardoned warns

        },

        "note": {  # stores member, who noted, note id, and note

        },

        "noteid": 0,

        "unban_queue": {  # stores members who need to be unbanned and what time to unban

        },

        "unmute_queue": {

        }
    }

    def __init__(self, bot) -> None:
        super().__init__(bot)

    async def load_cache(self):
        await super().load_cache()

        for key, value in list(self.cache["unban_queue"].items()):
            await self._unban(key, value)

        for key, value in list(self.cache["unmute_queue"].items()):
            await self._unmute(key,value)

    # @discord.default_permissions(ban_members=True)

#----------------------------------------ban and unbans----------------------------------------#

    @commands.slash_command(name="ban", description="Bans a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def ban(self, ctx: ApplicationContext, memberlist: discord.Option(str, description="The members you want to ban."),
                  duration: discord.Option(str, description="How long to ban the member for. Leave blank to permenantly ban.", default="inf"),
                  reason: discord.Option(str, description="Reason for ban.", default="")):
        """
        Bans a member via /ban [members] [duration: Optional] [reason: Optional]

        """
        after = None
        if duration != "inf":
            after = UserFriendlyTime()
            try:
                await after.convert(duration)
            except Exception as e:
                embed = discord.Embed(title="Error", description=e)
                await ctx.respond(embed=embed)
        memberlist = re.sub("[^0-9 ]", " ", memberlist)
        member = memberlist.split()
        successful_ids = ""
        failed_ids = ""
        for members in member:
            _member = await self.bot.fetch_user(members)
            try:
                await _member.send(f"You have been banned from {ctx.guild.name}. Reason: {reason}")
            except:
                self.logger.error(f"Can not message {members}.")
            try:
                await ctx.guild.ban(_member, reason=reason)
            except Exception as e:
                failed_ids += f"\n {members}"
                continue
            successful_ids += f"\n {members}"
            if after:
                self.cache["unban_queue"][str(members)] = after.dt
                await self._unban(members, after.dt)

            self.cache["ban"].setdefault(str(members), []).append(
                {"responsible": ctx.author.id, "reason": reason, "duration": duration, "time": datetime.now().timestamp()})

        await self.update_db()
        description = ""
        if successful_ids:
            description += f"Succesfully banned: {successful_ids}.\n"
            if after:
                description+=f"Unbanning at <t:{round(after.dt.timestamp())}:F>.\n."
        if failed_ids:
            description += f"Could not ban: {failed_ids}"
        if not description:
            description = f"No users parsed, please mention the user or use their id."
        embed = discord.Embed(
            title="Success", description=description)
        await ctx.respond(embed=embed)

    @commands.slash_command(name="unban", description="Unbans a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def unban(self, ctx: ApplicationContext, memberlist: discord.Option(str, description="The members you want to unban."),
                    reason: discord.Option(str, description="Reason for unban.", default="")):
        """
        Unbans a member via /unban [members] 

        """
        memberlist = re.sub("[^0-9 ]", " ", memberlist)
        member = memberlist.split()
        successful_ids = ""
        failed_ids = ""
        for members in member:
            _member = await self.bot.fetch_user(members)
            try:
                await self.bot.get_guild(self.bot.config["guild_id"]).unban(_member)
                successful_ids += f"\n{members}"
                self.cache["unban"].setdefault(str(members), []).append(
                    {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp()})
                
                try:
                    self.cache["unban_queue"].pop(members)
                except KeyError:
                    pass
            except:
                failed_ids += f"\n{members}"
        await self.update_db()
        description = ""
        if successful_ids:
            description += f"Successfully unbanned: {successful_ids}\n"
        if failed_ids:
            description += f"Users not banned: {failed_ids}"
        if not description:
            description = f"No users parsed, please mention the user or use their id."
        embed = discord.Embed(
            title="Success", description=description)
        await ctx.respond(embed=embed)

    async def _unban(self, member, time):
        now = datetime.utcnow()
        closetime = (time - now).total_seconds() if time else 0

        if closetime > 0:
            self.bot.loop.call_later(closetime, self._unban_after, member)
        else:
            await self._unban_helper(member)

    def _unban_after(self, member):  # bruh async stuff
        return self.bot.loop.create_task(self._unban_helper(member))

    async def _unban_helper(self, member):
        _member = await self.bot.fetch_user(member)
        try:
            await self.bot.get_guild(self.bot.config["guild_id"]).unban(_member)
            self.cache["unban"].setdefault(str(member), []).append(
                {"responsible": self.bot.application_id, "reason": f"Automated Unban", "time": datetime.now().timestamp()})
        except Exception as e:
            self.logger.error(f"{e}")
        self.cache["unban_queue"].pop(member)
        await self.update_db()

    @commands.slash_command(name="bans", description="Lists all bans and unbans for a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def bans(self, ctx: ApplicationContext, member: discord.Option(discord.Member, description="The members you want to get bans.")):
        """Lists all the bans and unbans for a member"""
        userid = str(member.id)
        if userid not in self.cache["ban"]:
            embed = discord.Embed(
                title=f"{member.name} ({member.id})", description="This user has not been banned.")
            await ctx.respond(embed=embed)
            return
        actionlist = copy.deepcopy(self.cache["ban"][userid])
        if userid in self.cache["unban"]:
            actionlist.extend(self.cache["unban"][userid])
        actionlist = sorted(actionlist, key=lambda d: d['time'])
        description = ""
        for action in actionlist:
            if "duration" in action:
                _moderator = await self.bot.fetch_user(action["responsible"])
                description += f'**Ban**\n Moderator: {_moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Duration: {action["duration"]} \n Date: <t:{round(action["time"])}:F> \n\n'
            else:
                _moderator = await self.bot.fetch_user(action["responsible"])
                description += f'**Unban**\n Moderator: {_moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Date: <t:{round(action["time"])}:F> \n\n'
        if not description:
            description = "This user has not been banned."
        embed = discord.Embed(
            title=f"{member.name} ({member.id})", description=description)
        await ctx.respond(embed=embed)


#----------------------------------------Kicks----------------------------------------#


    @commands.slash_command(name="kick", description="Kicks a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def kick(self, ctx: ApplicationContext, memberlist: discord.Option(str, description="The members you want to kick."),
                   reason: discord.Option(str, description="Reason for kick.", default="")):
        """
        Kicks a member via /kick [members] [reason: Optional]

        """
        memberlist = re.sub("[^0-9 ]", " ", memberlist)
        member = memberlist.split()
        successful_ids = ""
        failed_ids = ""
        for members in member:
            _member = await self.bot.fetch_user(members)
            try:
                await _member.send(f"You have been kicked from {ctx.guild.name}. Reason: {reason}")
            except:
                self.logger.error(f"Can not message {members}.")
            try:
                await ctx.guild.kick(_member, reason=reason)
            except Exception as e:
                failed_ids += f"\n {members}"
                continue
            successful_ids += f"\n {members}"

            self.cache["kick"].setdefault(str(members), []).append(
                {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp()})

        await self.update_db()
        description = ""
        if successful_ids:
            description += f"Succesfully kicked: {successful_ids}.\n"
        if failed_ids:
            description += f"Could not kick: {failed_ids}"
        if not description:
            description = f"No users parsed, please mention the user or use their id."
        embed = discord.Embed(
            title="Success", description=description)
        await ctx.respond(embed=embed)

    @commands.slash_command(name="kicks", description="Lists all bans and unbans for a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def kicks(self, ctx: ApplicationContext, member: discord.Option(discord.Member, description="The members you want to get bans.")):
        """Lists all the bans and unbans for a member"""
        userid = str(member.id)
        if userid not in self.cache["kick"]:
            embed = discord.Embed(
                title=f"{member.name} ({member.id})", description="This user has not been kicked.")
            await ctx.respond(embed=embed)
            return
        actionlist = copy.deepcopy(self.cache["kick"][userid])
        actionlist = sorted(actionlist, key=lambda d: d['time'])
        description = ""
        for action in actionlist:
            _moderator = await self.bot.fetch_user(action["responsible"])
            description += f'**Kick**\n Moderator: {_moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Date: <t:{round(action["time"])}:F> \n\n'
        if not description:
            description = "This user not been kicked."
        embed = discord.Embed(
            title=f"{member.name} ({member.id})", description=description)
        await ctx.respond(embed=embed)
#----------------------------------------Mute and Unmute----------------------------------------#

    @commands.slash_command(name="setmute", description="Sets the mute role")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def setmute(self, ctx: ApplicationContext, role: discord.Option(discord.Role, description="mute role")):
        """
        Sets the mute role via /mute [role]
        """
        self.cache["muterole"] = role.id
        await self.update_db()
        embed = discord.Embed(title="Success", description=f"Successfully set the mute role as {role.mention}")
        await ctx.respond(embed=embed)

    @commands.slash_command(name="mute", description="Mutes a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def mute(self, ctx: ApplicationContext, memberlist: discord.Option(str, description="The members you want to mute."),
                  duration: discord.Option(str, description="How long to mute the member for. Leave blank to permenant.", default="inf"),
                  reason: discord.Option(str, description="Reason for mute.", default="")):
        """
        Mutes a member via /mute [members] [duration: Optional] [reason: Optional]

        """
        if not self.cache["muterole"]:
            embed = discord.Embed(title="Error", description="Please set a mute role first by running /setmute [role]")
            await ctx.respond(embed=embed)
            return
        after = None
        if duration != "inf":
            after = UserFriendlyTime()
            try:
                await after.convert(duration)
            except Exception as e:
                embed = discord.Embed(title="Error", description=e)
                await ctx.respond(embed=embed)
                
        memberlist = re.sub("[^0-9 ]", " ", memberlist)
        member = memberlist.split()
        successful_ids = ""
        failed_ids = ""
        guild = self.bot.get_guild(self.bot.config["guild_id"])
        for members in member:
            _member = guild.get_member(int(members))
            roles = None
            try:
                dm = await _member.create_dm()
                await dm.send(f"You have been muted in {ctx.guild.name}. Reason: {reason}")
            except:
                logger.error(f"Can not message {members}.")
            try:
                role = [ctx.guild.get_role(self.cache["muterole"])]
                roleList= _member.roles
                roles = [None] * len(roleList)
                for idx, r in enumerate(roleList):
                    roles[idx] = r.id
                await _member.edit(roles = role)
            except Exception as e:
                logger.error(e)
                failed_ids += f"\n {members}"
                continue
            successful_ids += f"\n {members}"
            if after:
                self.cache["unmute_queue"][str(members)] = after.dt
                await self._unmute(members, after.dt)

            self.cache["mute"].setdefault(str(members), []).append(
                    {"responsible": ctx.author.id, "reason": reason, "duration": duration, "time": datetime.now().timestamp(), "roles": roles})

        await self.update_db()
        description = ""
        if successful_ids:
            description += f"Succesfully muted: {successful_ids}.\n"
            if after:
                description+=f"Unmuting at <t:{round(after.dt.timestamp())}:F>.\n."
        if failed_ids:
            description += f"Could not mute: {failed_ids}"
        if not description:
            description = f"No users parsed, please mention the user or use their id."
        embed = discord.Embed(
            title="Success", description=description)
        await ctx.respond(embed=embed)

    @commands.slash_command(name="unmute", description="Unmutes a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def unmute(self, ctx: ApplicationContext, memberlist: discord.Option(str, description="The members you want to unmute."),
                    reason: discord.Option(str, description="Reason for unmute.", default="")):
        """
        Unmutes a member via /unmute [members] [reason: optional]

        """
        memberlist = re.sub("[^0-9 ]", " ", memberlist)
        member = memberlist.split()
        successful_ids = ""
        failed_ids = ""
        guild = self.bot.get_guild(self.bot.config["guild_id"])
        muteRole = guild.get_role(self.cache["muterole"])
        for members in member:
            _member = guild.get_member(int(members))
            if muteRole in _member.roles:
                listRoles = [None] * len(self.cache["mute"][members][-1]["roles"])
                for idx, r in enumerate(self.cache["mute"][members][-1]["roles"]):
                    listRoles[idx] = guild.get_role(r)
                await _member.edit(roles=listRoles)
                self.cache["unmute"].setdefault(str(members), []).append(
                    {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp()})

                try: 
                    self.cache["unmute_queue"].pop(str(members)) #incase unmute before auto unmute
                except KeyError:
                    pass
                successful_ids+=f"\n{members}"
            else:
                failed_ids += f"\n{members}"
        await self.update_db()
        description = ""
        if successful_ids:
            description += f"Successfully unmuted: {successful_ids}\n"
        if failed_ids:
            description += f"Users not unmuted: {failed_ids}"
        if not description:
            description = f"No users parsed, please mention the user or use their id."
        embed = discord.Embed(
            title="Success", description=description)
        await ctx.respond(embed=embed)


    async def _unmute(self, member, time):
        now = datetime.utcnow()
        closetime = (time - now).total_seconds() if time else 0

        if closetime > 0:
            self.bot.loop.call_later(closetime, self._unmute_after, member)
        else:
            await self._unmute_helper(member)

    def _unmute_after(self, member):  # bruh async stuff
        return self.bot.loop.create_task(self._unmute_helper(member))

    async def _unmute_helper(self, member):
        try:
            guild = self.bot.get_guild(self.bot.config["guild_id"])
            members = guild.get_member(int(member))
            listRoles = [None] * len(self.cache["mute"][member][-1]["roles"])
            for idx, r in enumerate(self.cache["mute"][member][-1]["roles"]):
                listRoles[idx] = guild.get_role(r)
            await members.edit(roles=listRoles)
            self.cache["unmute"].setdefault(str(member), []).append(
                {"responsible": self.bot.application_id, "reason": f"Automated Unmute", "time": datetime.now().timestamp()})
        except Exception as e:
            logger.error(f"{e}")
        self.cache["unmute_queue"].pop(member)
        await self.update_db()
    

    @commands.slash_command(name="mutes", description="Lists all mutes and unmutes for a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def mutes(self, ctx: ApplicationContext, member: discord.Option(discord.Member, description="The members you want to get mute history.")):
        """Lists all the mutes and unmutes for a member"""
        userid = str(member.id)
        if userid not in self.cache["mute"]:
            embed = discord.Embed(
                title=f"{member.name} ({member.id})", description="This user has not been muted.")
            await ctx.respond(embed=embed)
            return
        actionlist = copy.deepcopy(self.cache["mute"][userid])
        if userid in self.cache["unmute"]:
            actionlist.extend(self.cache["unmute"][userid])
        actionlist = sorted(actionlist, key=lambda d: d['time'])
        description = ""
        for action in actionlist:
            if "duration" in action:
                _moderator = await self.bot.fetch_user(action["responsible"])
                description += f'**Mute**\n Moderator: {_moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Duration: {action["duration"]} \n Date: <t:{round(action["time"])}:F> \n\n'
            else:
                _moderator = await self.bot.fetch_user(action["responsible"])
                description += f'**Unmute**\n Moderator: {_moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Date: <t:{round(action["time"])}:F> \n\n'
        if not description:
            description = "This user has not been muted."
        embed = discord.Embed(
            title=f"{member.name} ({member.id})", description=description)
        await ctx.respond(embed=embed)
#----------------------------------------Warn----------------------------------------#


    @commands.slash_command(name="warn", description="Warns a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def warn(self, ctx: ApplicationContext, memberlist: discord.Option(str, description="The members you want to warn."),
                   reason: discord.Option(str, description="Warn reason.")):
        """
        Warns a member via /warn [members] [reason]

        """
        memberlist = re.sub("[^0-9 ]", " ", memberlist)
        member = memberlist.split()
        successful_ids = ""
        failed_ids = ""
        for members in member:
            try:
                _member = await self.bot.fetch_user(members)
                await _member.send(f"You have been warned in {ctx.guild.name}. Reason: {reason}")
                successful_ids += f"\n {members}"
                self.cache["warn"].setdefault(str(members), []).append(
                    {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp(), "id": self.cache["warnid"]})
                self.cache["warnid"] += 1
            except:
                failed_ids += f"\n {members}"

        await self.update_db()
        description = ""
        if successful_ids:
            description += f"Succesfully warned: {successful_ids}.\n"
        if failed_ids:
            description += f"Could not message: {failed_ids}"
        if not description:
            description = f"No users parsed, please mention the user or use their id."
        embed = discord.Embed(
            title="Success", description=description)
        await ctx.respond(embed=embed)

    @commands.slash_command(name="pardon", description="Pardons a warn")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def pardon(self, ctx: ApplicationContext, warnid: discord.Option(int, description="Warn ID to pardon.")):
        user = None
        idx = None
        for key, value in self.cache["warn"].items():
            left = 0
            right = len(value)-1
            index = None
            while left <= right:
                mid = floor((left+right)/2)
                if value[mid]["id"] == warnid:
                    index = mid
                    break
                elif value[mid]["id"] < warnid:
                    left = mid + 1
                else:
                    right = mid-1
            else:
                continue
            user = key
            idx = index
            break
        embed = None
        if user:
            self.cache["pardon"].setdefault(user, []).append(
                self.cache["warn"][user][idx])
            self.cache["pardon"][user][-1]["pardoned_by"] = ctx.author.id
            self.cache["pardon"][user][-1]["pardon_time"] = datetime.now().timestamp()
            self.cache["warn"][user].pop(idx)
            await self.update_db()
            embed = discord.Embed(
                title="Success", description=f"Successfully pardoned warn of id {warnid}")
        else:
            embed = discord.Embed(
                title="Error", description="Invalid id, no warning found.")

        await ctx.respond(embed=embed)

    @commands.slash_command(name="warns", description="Lists all warns for a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def warns(self, ctx: ApplicationContext, member: discord.Option(discord.Member, description="The members you want to get warns.")):
        """Lists all the warns for a member"""
        userid = str(member.id)
        if userid not in self.cache["warn"]:
            embed = discord.Embed(
                title=f"{member.name} ({member.id})", description="This user has no warns")
            await ctx.respond(embed=embed)
            return
        actionlist = copy.deepcopy(self.cache["warn"][userid])
        if userid in self.cache["pardon"]:
            actionlist.extend(self.cache["pardon"][userid])
        actionlist = sorted(actionlist, key=lambda d: d['time'])
        description = ""
        for action in actionlist:
            if "pardoned_by" in action:
                _moderator = await self.bot.fetch_user(action["responsible"])
                _pardon_mod = await self.bot.fetch_user(action["pardoned_by"])
                description += f'**Warn id: {action["id"]}**\n Moderator: {_moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Date: <t:{round(action["time"])}:F> \n Pardoned by: {_pardon_mod.mention} ({action["pardoned_by"]}) \n Pardon date: <t:{round(action["pardon_time"])}:F> \n\n'
            else:
                _moderator = await self.bot.fetch_user(action["responsible"])
                description += f'**Warn id: {action["id"]}**\n Moderator: {_moderator.mention} ({action["responsible"]}) \n Reason: {action["reason"]} \n Date: <t:{round(action["time"])}:F> \n\n'
        if not description:
            description = "This user has no warns."
        embed = discord.Embed(
            title=f"{member.name} ({member.id})", description=description)
        await ctx.respond(embed=embed)


#----------------------------------------Note----------------------------------------#


    @commands.slash_command(name="note", description="Write a note about a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def note(self, ctx: ApplicationContext, memberlist: discord.Option(str, description="The members you want to write a note about."),
                   note: discord.Option(str, description="Note")):
        """
        Writes a note about a member member via /note [members] [note]

        """
        memberlist = re.sub("[^0-9 ]", " ", memberlist)
        member = memberlist.split()
        ids = ""
        for members in member:
            ids += f"\n{members}"
            self.cache["note"].setdefault(str(members), []).append(
                {"responsible": ctx.author.id, "note": note, "time": datetime.now().timestamp(), "id": self.cache["noteid"]})
            self.cache["noteid"] += 1

        await self.update_db()
        description = ""
        if ids:
            description = f"Successfully wrote a note for: {ids}"
        else:
            description = f"No users parsed, please mention the user or use their id."

        embed = discord.Embed(
            title="Success", description=description)
        await ctx.respond(embed=embed)

    delete = SlashCommandGroup("delete", "Manages notes")

    @delete.command(name="note", description="Deletes a note")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def remove_note(self, ctx: ApplicationContext, noteid: discord.Option(int, description="note ID to remove.")):
        user = None
        idx = None
        for key, value in self.cache["note"].items():
            left = 0
            right = len(value)-1
            index = None
            while left <= right:
                mid = floor((left+right)/2)
                if value[mid]["id"] == noteid:
                    index = mid
                    break
                elif value[mid]["id"] < noteid:
                    left = mid + 1
                else:
                    right = mid-1
            else:
                continue
            user = key
            idx = index
            break
        embed = None
        if user:
            self.cache["note"][user].pop(idx)
            await self.update_db()
            embed = discord.Embed(
                title="Success", description=f"Successfully delete note of id {noteid}")
        else:
            embed = discord.Embed(
                title="Error", description="Invalid id, no note found.")

        await ctx.respond(embed=embed)

    @commands.slash_command(name="notes", description="Lists all notes for a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def notes(self, ctx: ApplicationContext, member: discord.Option(discord.Member, description="The members you want to get notes.")):
        """Lists all the notes for a member"""
        userid = str(member.id)
        if userid not in self.cache["note"]:
            embed = discord.Embed(
                title=f"{member.name} ({member.id})", description="This user has no notes")
            await ctx.respond(embed=embed)
            return
        actionlist = copy.deepcopy(self.cache["note"][userid])
        actionlist = sorted(actionlist, key=lambda d: d['time'])
        description = ""
        for action in actionlist:
            _moderator = await self.bot.fetch_user(action["responsible"])
            description += f'**Note id: {action["id"]}**\n Moderator: {_moderator.mention} ({action["responsible"]}) \n Note: {action["note"]} \n Date: <t:{round(action["time"])}:F> \n\n'
        if not description:
            description = "This user has no notes."
        embed = discord.Embed(
            title=f"{member.name} ({member.id})", description=description)
        await ctx.respond(embed=embed)

#--------------------------------------------------------------------------------#
    @commands.slash_command(name="slowmode", description="Sets slowmode for a channel.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def slowmode(self, ctx: ApplicationContext, channel: discord.Option(discord.TextChannel, description="The channel you want to set slowmode.", default=None), time: discord.Option(str, description="The slowmode time.", default="0s")):
        regex = (r'((?P<hours>-?\d+)h)?'
                   r'((?P<minutes>-?\d+)m)?'
                   r'((?P<seconds>-?\d+)s)?')
        match = re.compile(regex, re.IGNORECASE).match(str(time))
        seconds = None

        if match:
            for k, v in match.groupdict().items():
                if v:
                    if not seconds:
                        seconds = 0
                    if k == 'hours':
                        seconds += int(v)*3600
                    elif k == "minutes":
                        seconds += int(v)*60
                    elif k == "seconds":
                        seconds += int(v)

        if seconds is None:
            embed = discord.Embed(title="Error", description=f"Could not parse time: {time}. Make sure it is in the form []h[]m[]s.")
            await ctx.respond(embed=embed)
            return

        if seconds > 21600:
            embed = discord.Embed(title="Error", description=f"Parsed time {seconds}s too large. Maximum slowmode is 6h.")
            await ctx.respond(embed=embed)
            return
        
        if not channel:
            channel = ctx.channel

        await channel.edit(slowmode_delay = seconds)

        embed = discord.Embed(title="Success!", description=f"Successfully set slowmode in {channel.mention} to {seconds}s.")
        await ctx.respond(embed=embed)



def setup(bot):
    bot.add_cog(Moderation(bot))

