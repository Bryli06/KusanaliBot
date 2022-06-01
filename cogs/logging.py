from copy import deepcopy
from datetime import datetime
import time
import discord
from discord.ext import commands

from discord import ApplicationContext, CategoryChannel, ChannelType, Colour, EmbedField, ForumChannel, Interaction, OptionChoice, Permissions, SlashCommandGroup, StageChannel, TextChannel, VoiceChannel

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel


class Logging(BaseCog):
    _id = "logging"

    default_cache = {
        "logChannel": None,
        "modChannel": None,
        "msgChannel": None,
        "srvChannel": None,
        "jlvChannel": None,
        "mbrChannel": None
    }

    _lg = SlashCommandGroup("log", "Contains all the commands for logging.")

    def __init__(self, bot) -> None:
        super().__init__(bot)

#--------------------------------------moderation logs---------------------------------------#

    # TODO implement a custom event for moderation activity

#----------------------------------------message logs----------------------------------------#

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

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

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["msgChannel"])
        await chn.send(embed=embed)

    @ commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

        embed = discord.Embed(title=f"Message edited in #{before.channel.name}",
                              description=f"**Before:** {before.content}\n**After:** {after.content}\n", timestamp=after.edited_at, colour=Colour.blue())

        embed.set_author(
            name=f"{before.author.name}#{before.author.discriminator}", icon_url=before.author.avatar)
        embed.set_footer(text=before.author.id)

        if self.cache["msgChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["msgChannel"])
        await chn.send(embed=embed)

#-----------------------------------------server logs----------------------------------------#

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

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

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["srvChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

        embed = discord.Embed(title=f"{channel.type.name.capitalize()} channel deleted",
                              description=f"**Name:** {channel.name}\n{f'**Category:** {channel.category}' if channel.category != None else ''}\n",
                              timestamp=datetime.now(), colour=Colour.red())

        embed.set_footer(text=channel.id)

        if self.cache["srvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["srvChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

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

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["srvChannel"])

        if len(embed.fields) > 0:
            await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

        embed = discord.Embed(title="New role created",
                              description=f"**Name:** {role.name}\n**Color:** {role.colour}\n**Mentionable:** {role.mentionable}\n**Displayed separately:** {role.hoist}",
                              timestamp=role.created_at, colour=Colour.green())

        embed.set_footer(text=role.id)

        if self.cache["srvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["srvChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

        embed = discord.Embed(title=f"Role \"{role.name}\" removed",
                              description=f"**Name:** {role.name}\n**Color:** {role.colour}\n**Mentionable:** {role.mentionable}\n**Displayed separately:** {role.hoist}\n**Position:** {role.position}",
                              timestamp=datetime.now(), colour=Colour.red())

        embed.set_footer(text=role.id)

        if self.cache["srvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["srvChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

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

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["srvChannel"])

        if len(embed.fields) > 0 or len(embed.fields) == 1 and before.position == after.position:
            await chn.send(embed=embed)

#---------------------------------------join/leave logs--------------------------------------#

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

        def ordinal(n): return "%d%s" % (
            n, "tsnrhtdd"[(n//10 % 10 != 1)*(n % 10 < 4)*n % 10::4])

        embed = discord.Embed(title=f"New member joined",
                              description=f"{member.mention} is the {ordinal(guild.member_count)} member.",
                              timestamp=member.joined_at, colour=Colour.green())

        embed.set_author(
            name=f"{member.name}#{member.discriminator}", icon_url=member.avatar)
        embed.set_footer(text=member.id)

        if self.cache["jlvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["jlvChannel"])
        await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

        embed = discord.Embed(title=f"Member left",
                              description=f"{member.mention} joined <t:{int(time.mktime(member.joined_at.timetuple()))}:R>.",
                              timestamp=datetime.now(), colour=Colour.green())

        embed.set_author(
            name=f"{member.name}#{member.discriminator}", icon_url=member.avatar)
        embed.set_footer(text=member.id)

        if self.cache["jlvChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["jlvChannel"])
        await chn.send(embed=embed)

#-----------------------------------------member logs----------------------------------------#

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

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

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["mbrChannel"])

        if len(embed.fields) > 0:
            await chn.send(embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.Member, after: discord.Member):
        guild = self.bot.get_guild(self.bot.config["guild_id"])

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

        embed.set_thumbnail(url=after.avatar.url)

        embed.set_footer(text=before.id)

        if self.cache["mbrChannel"] == None:
            if self.cache["logChannel"] == None:
                return

            chn = guild.get_channel(self.cache["logChannel"])
            await chn.send(embed=embed)

            return

        chn = guild.get_channel(self.cache["mbrChannel"])

        if len(embed.fields) > 0:
            await chn.send(embed=embed)

    @ _lg.command(name="set", description="Sets a log channel.")
    @ checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _lg_set(self, ctx: ApplicationContext, log_channel: discord.Option(str, "The channel you want to set. Log channel is the default if none is set.",
                      choices=[OptionChoice("Logs channel", "logChannel"), OptionChoice("Moderation logs channel", "modChannel"), OptionChoice("Message logs channel", "msgChannel"),
                               OptionChoice("Server logs channel", "srvChannel"), OptionChoice("Join/Leave logs channel", "jlvChannel"), OptionChoice("Member logs channel", "mbrChannel")]),
                      channel: discord.Option(discord.TextChannel, "The channel id you want to set the channel as.")):
        if ctx.guild.get_channel(channel.id) == None:
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
            "mbrChannel": "member "
        }

        embed = discord.Embed(
            title="Success", description=f"Set {channel_names[log_channel]}logs channel as {channel.mention}.")
        await ctx.respond(embed=embed)

    @ _lg.command(name="clear", description="Clears a log channel.")
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


def setup(bot):
    bot.add_cog(Logging(bot))
