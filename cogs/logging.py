import traceback as tb
from copy import deepcopy
from datetime import datetime
import time
import discord
from discord.ext import commands

from discord import ApplicationContext, CategoryChannel, ChannelType, Colour, Embed, EmbedField, ForumChannel, Interaction, OptionChoice, Permissions, SlashCommandGroup, StageChannel, TextChannel, VoiceChannel

from core import checks
from core import context
from core.base_cog import BaseCog
from core.checks import PermissionLevel
from core import logger


class Logging(BaseCog):
    _id = "logging"

    default_cache = {
        "logChannel": None,
        "modChannel": None,
        "msgChannel": None,
        "srvChannel": None,
        "jlvChannel": None,
        "mbrChannel": None,
        "errChannel": None
    }

    _lg = SlashCommandGroup("log", "Contains all the commands for logging.")

#--------------------------------------moderation logs---------------------------------------#

    @commands.Cog.listener()
    async def on_member_ban(self, ctx):
        embed = Embed(title="Member banned",
                      timestamp=ctx.timestamp, colour=Colour.red)

        embed.add_field(name="Member banned",
                        value=f"{ctx.member.name}#{ctx.member.discriminator}")
        embed.add_field(name="Banned by", value=f"{ctx.moderator.mention}")

        if ctx.duration:
            embed.add_field(name="Duration",
                            value=f"Until <t:{int(ctx.duration)}:F>")

        if ctx.reason:
            embed.add_field(name="Reason", value=ctx.reason)

        if self.cache["modChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["modChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, ctx):
        embed = Embed(title="Member unbanned",
                      timestamp=ctx.timestamp, colour=Colour.green)

        embed.add_field(name="Member unbanned",
                        value=f"{ctx.member.name}#{ctx.member.discriminator}")
        embed.add_field(name="Unbanned by", value=f"{ctx.moderator.mention}")

        if ctx.reason:
            embed.add_field(name="Reason", value=ctx.reason)

        if self.cache["modChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["modChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_warn(self, ctx):
        embed = Embed(title="Member warned",
                      timestamp=ctx.timestamp, colour=Colour.red)

        embed.add_field(name="Member warned",
                        value=f"{ctx.member.name}#{ctx.member.discriminator}")
        embed.add_field(name="Warned by", value=f"{ctx.moderator.mention}")

        if ctx.reason:
            embed.add_field(name="Reason", value=ctx.reason)

        if ctx.id:
            embed.add_field(name="Warn ID", value=ctx.id)

        if self.cache["modChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["modChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_pardon(self, ctx):
        embed = Embed(title="Member pardoned",
                      timestamp=ctx.timestamp, colour=Colour.green)

        embed.add_field(name="Member pardoned",
                        value=f"{ctx.member.name}#{ctx.member.discriminator}")
        embed.add_field(name="Pardoned by", value=f"{ctx.moderator.mention}")

        if ctx.reason:
            embed.add_field(name="Reason", value=ctx.reason)

        if ctx.id:
            embed.add_field(name="Warn ID", value=ctx.id)

        if self.cache["modChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["modChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_kick(self, ctx):
        embed = Embed(title="Member kicked",
                      timestamp=ctx.timestamp, colour=Colour.red)

        embed.add_field(name="Member kicked",
                        value=f"{ctx.member.name}#{ctx.member.discriminator}")
        embed.add_field(name="Kicked by", value=f"{ctx.moderator.mention}")

        if ctx.reason:
            embed.add_field(name="Reason", value=ctx.reason)

        if self.cache["modChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["modChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_mute(self, ctx):
        embed = Embed(title="Member muted",
                      timestamp=ctx.timestamp, colour=Colour.red)

        embed.add_field(name="Member muted",
                        value=f"{ctx.member.name}#{ctx.member.discriminator}")
        embed.add_field(name="Muted by", value=f"{ctx.moderator.mention}")

        if ctx.duration:
            embed.add_field(name="Duration",
                            value=f"Until <t:{int(ctx.duration)}:F>")

        if ctx.reason:
            embed.add_field(name="Reason", value=ctx.reason)

        if self.cache["modChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["modChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unmute(self, ctx):
        embed = Embed(title="Member unmuted",
                      timestamp=ctx.timestamp, colour=Colour.green)

        embed.add_field(name="Member unmuted",
                        value=f"{ctx.member.name}#{ctx.member.discriminator}")
        embed.add_field(name="Unmuted by", value=f"{ctx.moderator.mention}")

        if ctx.reason:
            embed.add_field(name="Reason", value=ctx.reason)

        if self.cache["modChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["modChannel"])
        await chn.send(embed=embed)

#----------------------------------------message logs----------------------------------------#

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return

        embed = discord.Embed(title=f"Message deleted in #{message.channel.name}",
                              description=message.content, timestamp=message.created_at, colour=Colour.red())

        if len(message.attachments) > 0:
            value = ""
            for attachment in message.attachments:
                value += f"**{attachment.content_type}:** [{attachment.filename}]({attachment.url})\n"

            embed.add_field(name="Attachments", value=value, inline=False)

        embed.set_author(
            name=f"{message.author.name}#{message.author.discriminator}", icon_url=message.author.avatar)
        embed.set_footer(text=message.author.id)

        if self.cache["msgChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["msgChannel"])
        await chn.send(embed=embed)

    @ commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return

        if before.content == after.content:
            return

        embed = discord.Embed(title=f"Message edited in #{before.channel.name}",
                              description=f"**Before:** {before.content}\n**After:** {after.content}\n", timestamp=after.edited_at, colour=Colour.blue())

        embed.set_author(
            name=f"{before.author.name}#{before.author.discriminator}", icon_url=before.author.avatar)
        embed.set_footer(text=before.author.id)

        if self.cache["msgChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["msgChannel"])
        await chn.send(embed=embed)

#-----------------------------------------server logs----------------------------------------#

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):

        embed = discord.Embed(title=f"{channel.type.name.capitalize()} channel created",
                              description=f"**Name:** {channel.name}\n{f'**Category:** {channel.category}' if channel.category != None else ''}\n",
                              timestamp=channel.created_at, colour=Colour.green())

        for target in channel.overwrites:
            embed.add_field(name=f"Overwrites for {target.name}", value="".join(
                [f"**{permission.replace('_', ' ').capitalize()}:** {'🟩' if value else '🟥'}\n" if value != None else "" for permission, value in channel.overwrites[target]]), inline=False)

        fields = deepcopy(embed.fields)
        for field in fields:
            if field.value == "":
                embed.fields.remove(field)

        embed.set_footer(text=channel.id)

        if self.cache["srvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["srvChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):

        embed = discord.Embed(title=f"{channel.type.name.capitalize()} channel deleted",
                              description=f"**Name:** {channel.name}\n{f'**Category:** {channel.category}' if channel.category != None else ''}\n",
                              timestamp=datetime.now(), colour=Colour.red())

        embed.set_footer(text=channel.id)

        if self.cache["srvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["srvChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):

        embed = discord.Embed(
            title=f"{before.type.name.capitalize()} channel updated",
            description=f"Channel {before.mention} updated.",
            timestamp=datetime.now(), colour=Colour.blue())

        before_value = [
            f"**Name:** {before.name}\n" if before.name != after.name else "",
            f"**Topic:** {before.topic}\n" if before.type.name == 'text' and before.topic != after.topic else ""
        ]

        after_value = [
            f"**Name:** {after.name}\n" if before.name != after.name else "",
            f"**Topic:** {after.topic}\n" if before.type.name == 'text' and before.topic != after.topic else ""
        ]

        if before_value.count("") != len(before_value):
            embed.add_field(name="Before", value="".join(before_value))
            embed.add_field(name="After", value="".join(after_value))

        for target in before.overwrites:
            if target not in after.overwrites:
                embed.add_field(
                    name=f"Overwrites for {target.name}", value="**Removed**", inline=False)
                continue

            if before.overwrites[target] == after.overwrites[target]:
                continue

            after_permissions = {k: v for k,
                                 v in iter(after.overwrites[target])}

            embed.add_field(name=f"Overwrites for {target.name}", value="".join(
                [f"**{before_permission[0].replace('_', ' ').capitalize()}:** {'🟩' if before_permission[1] else '🟥' if before_permission[1] != None else '⬜'} ➜ {'🟩' if after_permissions[before_permission[0]] else '🟥' if after_permissions[before_permission[0]] != None else '⬜'}\n"
                 if before_permission[1] != after_permissions[before_permission[0]] else ""
                 for before_permission in before.overwrites[target]]), inline=False)

        embed.set_footer(text=before.id)

        if self.cache["srvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["srvChannel"])

        if len(embed.fields) > 0:
            await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):

        embed = discord.Embed(title="New role created",
                              description=f"**Name:** {role.name}\n**Color:** {role.colour}\n**Mentionable:** {role.mentionable}\n**Displayed separately:** {role.hoist}",
                              timestamp=role.created_at, colour=Colour.green())

        embed.set_footer(text=role.id)

        if self.cache["srvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["srvChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):

        embed = discord.Embed(title=f"Role \"{role.name}\" removed",
                              description=f"**Name:** {role.name}\n**Color:** {role.colour}\n**Mentionable:** {role.mentionable}\n**Displayed separately:** {role.hoist}\n**Position:** {role.position}",
                              timestamp=datetime.now(), colour=Colour.red())

        embed.set_footer(text=role.id)

        if self.cache["srvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["srvChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):

        embed = discord.Embed(title=f"Role \"{before.name}\" updated",
                              description=f"Role {before.mention} updated.",
                              timestamp=datetime.now(), colour=Colour.blue())

        before_value = [
            f"**Name:** {before.name}\n" if before.name != after.name else "",
            f"**Color:** {before.colour}\n" if before.colour != after.colour else "",
            f"**Mentionable:** {before.mentionable}\n" if before.mentionable != after.mentionable else "",
            f"**Separate:** {before.hoist}\n" if before.hoist != after.hoist else "",
            f"**Position:** {before.position}\n" if before.position != after.position else ""
        ]

        after_value = [
            f"**Name:** {after.name}\n" if before.name != after.name else "",
            f"**Color:** {after.colour}\n" if before.colour != after.colour else "",
            f"**Mentionable:** {after.mentionable}\n" if before.mentionable != after.mentionable else "",
            f"**Separate:** {after.hoist}\n" if before.hoist != after.hoist else "",
            f"**Position:** {after.position}\n" if before.position != after.position else ""
        ]

        if before_value.count("") != len(before_value):
            embed.add_field(name="Before", value="".join(before_value))
            embed.add_field(name="After", value="".join(after_value))

        if before.permissions != after.permissions:
            after_permissions = {k: v for k, v in iter(after.permissions)}

            embed.add_field(name="Permissions", value="".join(
                [f"**{before_permission[0].replace('_', ' ').capitalize()}:** {'🟩' if before_permission[1] else '🟥'} ➜ {'🟩' if after_permissions[before_permission[0]] else '🟥'}\n"
                 if before_permission[1] != after_permissions[before_permission[0]] else ""
                 for before_permission in before.permissions]), inline=False)

        embed.set_footer(text=before.id)

        if self.cache["srvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["srvChannel"])

        if len(embed.fields) > 0 or len(embed.fields) == 1 and before.position == after.position:
            await chn.send(embed=embed)

#---------------------------------------join/leave logs--------------------------------------#

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        def ordinal(n): return "%d%s" % (
            n, "tsnrhtdd"[(n//10 % 10 != 1)*(n % 10 < 4)*n % 10::4])

        embed = discord.Embed(title=f"New member joined",
                              description=f"{member.mention} is the {ordinal(self.guild.member_count)} member.",
                              timestamp=member.joined_at, colour=Colour.green())

        embed.set_author(
            name=f"{member.name}#{member.discriminator}", icon_url=member.avatar)
        embed.set_footer(text=member.id)

        if self.cache["jlvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["jlvChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return

        embed = discord.Embed(title=f"Member left",
                              description=f"{member.mention} joined <t:{int(time.mktime(member.joined_at.timetuple()))}:R>.",
                              timestamp=datetime.now(), colour=Colour.red())

        embed.set_author(
            name=f"{member.name}#{member.discriminator}", icon_url=member.avatar)
        embed.set_footer(text=member.id)

        if self.cache["jlvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["jlvChannel"])
        await chn.send(embed=embed)

#-----------------------------------------member logs----------------------------------------#

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot:
            return

        embed = discord.Embed(
            title=f"Member updated",
            description=f"Member {before.mention} updated.",
            timestamp=datetime.now(), colour=Colour.blue())

        embed.set_author(
            name=f"{after.name}#{after.discriminator}", icon_url=after.avatar)

        before_value = [
            f"**Nickname:** {before.nick}\n" if before.nick != after.nick else ""
        ]

        after_value = [
            f"**Nickname:** {after.nick}\n" if before.nick != after.nick else ""
        ]

        if before_value.count("") != len(before_value):
            embed.add_field(name="Before", value="".join(before_value))
            embed.add_field(name="After", value="".join(after_value))

        added_roles = [
            role.mention for role in after.roles if role not in before.roles]
        removed_roles = [
            role.mention for role in before.roles if role not in after.roles]

        if len(added_roles) > 0:
            embed.add_field(name="Added roles", value=" ".join(added_roles))

        if len(removed_roles) > 0:
            embed.add_field(name="Removed roles",
                            value=" ".join(removed_roles))

        embed.set_footer(text=before.id)

        if self.cache["mbrChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["mbrChannel"])

        if len(embed.fields) > 0:
            await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.Member, after: discord.Member):
        if before.bot:
            return

        embed = discord.Embed(
            title=f"User updated",
            description=f"User {before.mention} updated.",
            timestamp=datetime.now(), colour=Colour.blue())

        embed.set_author(
            name=f"{after.name}#{after.discriminator}", icon_url=after.avatar)

        before_value = [
            f"**Name:** {before.name}#{before.discriminator}\n" if before.name != after.name or before.discriminator != after.discriminator else ""
        ]

        after_value = [
            f"**Name:** {after.name}#{after.discriminator}\n" if before.name != after.name or before.discriminator != after.discriminator else ""
        ]

        if before_value.count("") != len(before_value):
            embed.add_field(name="Before", value="".join(before_value))
            embed.add_field(name="After", value="".join(after_value))

        embed.set_thumbnail(url=after.avatar)

        embed.set_footer(text=before.id)

        if self.cache["mbrChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["mbrChannel"])

        await chn.send(embed=embed)

#------------------------------------------error logs----------------------------------------#

    @commands.Cog.listener()
    async def on_error(self, exception: Exception, hint: str = "", suggestion: str = ""):

        embed = discord.Embed(title="Error")

        embed.add_field(name="Exception", value=f"`{exception}`", inline=False)
        embed.add_field(
            name="Traceback", value=f"`{''.join(tb.format_exception(type(exception), exception, exception.__traceback__))}`", inline=False)

        if hint != "":
            embed.add_field(name="Hint", value=hint, inline=False)

        if suggestion != "":
            embed.add_field(name="Suggestion", value=suggestion, inline=False)

        if self.cache["errChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["errChannel"])

        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, exception: discord.DiscordException):

        embed = discord.Embed(
            title="Error",
            description=f"It seems an error has occured.\nError:`{exception}`\nIf you believe this to be a bug please report it to the technical mod team.")

        await ctx.respond(embed=embed)

        embed.description = f"Command `{ctx.command}` has raised an error.\nError with traceback\n`{''.join(tb.format_exception(None, exception, exception.__traceback__))}`"

        if self.cache["errChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = await self.guild.fetch_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = await self.guild.fetch_channel(self.cache["errChannel"])

        await chn.send(embed=embed)

    @ _lg.command(name="set", description="Sets a logs channel.")
    @ checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _lg_set(self, ctx: ApplicationContext, log_channel: discord.Option(str, "The channel you want to set. Log channel is the default if none is set.",
                      choices=[OptionChoice("Logs channel", "logChannel"), OptionChoice("Moderation logs channel", "modChannel"), OptionChoice("Message logs channel", "msgChannel"),
                               OptionChoice("Server logs channel", "srvChannel"), OptionChoice(
                                   "Join/Leave logs channel", "jlvChannel"), OptionChoice("Member logs channel", "mbrChannel"),
                               OptionChoice("Error logs channel", "errChannel")]),
                      channel: discord.Option(discord.TextChannel, "The channel id you want to set the channel as.")):
        if ctx.self.guild.get_channel(channel.id) == None:
            embed = discord.Embed(
                title="Error", description="Channel not found in the server.")
            await ctx.respond(embed=embed)

            return

        self.cache[log_channel] = channel.id
        await self.update_db()

        channel_names = {
            "logChannel": "",
            "modChannel": "moderation ",
            "msgChannel": "message ",
            "srvChannel": "server ",
            "jlvChannel": "join/leave ",
            "mbrChannel": "member ",
            "errChannel": "error "
        }

        embed = discord.Embed(
            title="Success", description=f"Set {channel_names[log_channel]}logs channel as {channel.mention}.")
        await ctx.respond(embed=embed)

    @ _lg.command(name="clear", description="Clears a logs channel.")
    @ checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _lg_clear(self, ctx: ApplicationContext, log_channel: discord.Option(str, "The channel you want to clear.",
                        choices=[OptionChoice("Logs channel", "logChannel"), OptionChoice("Moderation logs channel", "modChannel"), OptionChoice("Message logs channel", "msgChannel"),
                                 OptionChoice("Server logs channel", "srvChannel"), OptionChoice("Join/Leave logs channel", "jlvChannel"), OptionChoice("Member logs channel", "mbrChannel")])):
        if self.cache[log_channel] == None:
            embed = discord.Embed(
                title="Error", description="Channel is not set.")
            await ctx.respond(embed=embed)

            return

        self.cache[log_channel] = None
        await self.update_db()

        channel_names = {
            "logChannel": "",
            "modChannel": "moderation ",
            "msgChannel": "message ",
            "srvChannel": "server ",
            "jlvChannel": "join/leave ",
            "mbrChannel": "member "
        }

        embed = discord.Embed(
            title="Success", description=f"Cleared {channel_names[log_channel]}logs channel.")
        await ctx.respond(embed=embed)

    @ _lg.command(name="list", description="Lists the logs channels.")
    @ checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _lg_list(self, ctx: ApplicationContext):
        channel_names = {
            "logChannel": "All ",
            "modChannel": "Moderation ",
            "msgChannel": "Message ",
            "srvChannel": "Server ",
            "jlvChannel": "Join/Leave ",
            "mbrChannel": "Member ",
            "errChannel": "Error "
        }

        embed = discord.Embed(title="Logs channels")

        for channel in self.cache:
            if channel == "_id":
                continue

            embed.add_field(name=f"{channel_names[channel]} logs channel",
                            value=f"<#{self.cache[channel]}>" if self.cache[channel] != None else "No channel set.", inline=False)

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Logging(bot))
