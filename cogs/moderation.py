import discord
from discord.ext import commands
from discord import SlashCommandGroup, ApplicationContext, SlashCommand, default_permissions, option
from discord.commands import Option
from datetime import datetime

import copy
from math import floor
import re

from core.time import UserFriendlyTime
from core import checks
from core.checks import PermissionLevel
from core.logger import get_logger
from core import config

logger = get_logger(__name__)


class Moderation(commands.Cog):
    _id = "moderation"

    default_cache = {
        "ban": {  # stores member who is banned, who banned, and reason for ban

        },
        "unban": {  # stores unban log and who unbanned member

        },
        "kick": {  # stores member who is kicked, who kicked, and reason for kick

        },

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

        for key, value in list(self.cache["unban_queue"].items()):
            await self._unban(key, value)

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
            await after.convert(duration)
        memberlist = re.sub("[^0-9 ]", " ", memberlist)
        member = memberlist.split()
        successful_ids = ""
        failed_ids = ""
        for members in member:
            _member = await self.bot.fetch_user(members)
            try:
                await _member.send(f"You have been banned from {ctx.guild.name}. Reason: {reason}")
            except:
                logger.error(f"Can not message {members}.")
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
            description += f"Succesfully banned: {successful_ids}."
        if failed_ids:
            description += f"Could not ban: {failed_ids}"
        embed = discord.Embed(
            title="Success", description=description)
        await ctx.respond(embed=embed)

    @commands.slash_command(name="unban", description="Unbans a member")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def unban(self, ctx: ApplicationContext, memberlist: discord.Option(str, description="The members you want to unban."),
                    reason: discord.Option(str, description="Reason for ban.", default="")):
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
            except:
                failed_ids += f"\n{members}"
        await self.update_db()
        description = ""
        if successful_ids:
            description += f"Successfully unbanned: {successful_ids}"
        if failed_ids:
            description += f"Users not banned: {failed_ids}"
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
            logger.error(f"{e}")
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
                logger.error(f"Can not message {members}.")
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
            description += f"Succesfully kicked: {successful_ids}."
        if failed_ids:
            description += f"Could not kick: {failed_ids}"
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
            _member = await self.bot.fetch_user(members)
            try:
                await _member.send(f"You have been warned in {ctx.guild.name}. Reason: {reason}")
                successful_ids += f"\n {members}"
            except:
                failed_ids += f"\n {members}"

            self.cache["warn"].setdefault(str(members), []).append(
                {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp(), "id": self.cache["warnid"]})
            self.cache["warnid"] += 1

        await self.update_db()
        description = ""
        if successful_ids:
            description += f"Succesfully warned: {successful_ids}."
        if failed_ids:
            description += f"Could not message: {failed_ids}"
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
        embed = discord.Embed(
            title="Success", description=f"Successfully wrote a note for: {ids}")
        await ctx.respond(embed=embed)

    delete = SlashCommandGroup("delete", "Manages notes")

    @delete.command(name="note", description="Deletes a note")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def remove_warn(self, ctx: ApplicationContext, noteid: discord.Option(int, description="note ID to remove.")):
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


def setup(bot):
    bot.add_cog(Moderation(bot))
