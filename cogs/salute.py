import discord
from discord.ext import commands

from discord import Colour

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel

import re
import requests

import copy


class Salute(BaseCog):
    _id = "salute"

    default_cache = {
        "channels": {
            "welcome": "",
            "farewell": ""
        },
        "messages": {
            "welcome": "",
            "farewell": ""
        },
        "embeds": {
            "welcome": {},
            "farewell": {}
        }
    }

    _slt = discord.SlashCommandGroup("salute", "Manages all the join/leave events.",
                                     default_member_permissions=discord.Permissions(manage_messages=True))

    _chn = _slt.create_subgroup(
        "channels", "Manages the channels for the join/leave events.")
    _msg = _slt.create_subgroup(
        "message", "Manages the messages for the join/leave events.")
    _emb = _slt.create_subgroup(
        "embed", "Manages thee embeds for the join/leave events.")

    async def translate_message(self, memeber: discord.Member, message, channel: discord.TextChannel):
        """
        Replaces blocks with the appropiate text value.
        
        """

        blocks = {
            "{user}": memeber.display_name,
            "{mention}": memeber.mention,
            "{channel}": channel.mention
        }

        regex = r"{[^{}]*}"
        matches = list(dict.fromkeys(re.findall(regex, message)))

        for match in matches:
            if match not in blocks:
                continue

            message = message.replace(match, blocks[match])

        return message

    async def pastebin_to_json(self, url):
        """
        Converts a pastebin link to a json for embeds.
        
        """

        regex = r"(?<=com/)"
        url = re.sub(regex, "raw/", url)

        json_file = requests.get(url).json()

        return json_file

    async def json_to_embed(self, json_file):
        """
        Converts a json to an embed.
        
        """

        return discord.Embed.from_dict(json_file)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if self.cache["channels"]["welcome"] == "":
            return

        channel: discord.TextChannel = await self.guild.fetch_channel(int(self.cache["channels"]["welcome"]))

        if channel == None:
            return

        if self.cache["messages"]["welcome"] is not None and self.cache["messages"]["welcome"] != "":
            await channel.send(await self.translate_message(member, self.cache["messages"]["welcome"], channel))

        if self.cache["embeds"]["welcome"] is not None and self.cache["embeds"]["welcome"] != "":
            wlc_embed = copy.deepcopy(self.cache["embeds"]["welcome"])

            try:
                wlc_embed["title"] = await self.translate_message(member, wlc_embed["title"], channel)
            except KeyError:
                pass
            
            try:
                wlc_embed["description"] = await self.translate_message(member, wlc_embed["description"], channel)
            except KeyError:
                pass

            await channel.send(embed=await self.json_to_embed(wlc_embed))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if self.cache["channels"]["farewell"] == "":
            return

        channel: discord.TextChannel = await self.guild.fetch_channel(int(self.cache["channels"]["farewell"]))

        if channel == None:
            return

        if self.cache["messages"]["farewell"] is not None and self.cache["messages"]["farewell"] != "":
            await channel.send(await self.translate_message(member, self.cache["messages"]["farewell"], channel))

        if self.cache["embeds"]["farewell"] is not None and self.cache["embeds"]["farewell"] != "":
            frw_embed = copy.deepcopy(self.cache["embeds"]["farewell"])

            try:
                frw_embed["title"] = await self.translate_message(member, frw_embed["title"], channel)
            except KeyError:
                pass

            try:
                frw_embed["description"] = await self.translate_message(member, frw_embed["description"], channel)
            except KeyError:
                pass

            await channel.send(embed=await self.json_to_embed(frw_embed))

    @_slt.command(name="test", description="Tests the join/leave events.")
    @checks.has_permissions(PermissionLevel.MOD)
    async def slt_test(self, ctx: discord.ApplicationContext):
        """
        Sends test welcome/farewell messages in the designated channels.

        """

        wlc_channel: discord.TextChannel = ctx.channel
        frw_channel: discord.TextChannel = ctx.channel

        if self.cache["channels"]["welcome"] != "":
            wlc_channel = await self.guild.fetch_channel(int(self.cache["channels"]["welcome"]))

        if self.cache["channels"]["welcome"] != "":
            frw_channel = await self.guild.fetch_channel(int(self.cache["channels"]["farewell"]))

        if self.cache["messages"]["welcome"] is not None and self.cache["messages"]["welcome"] != "":
            await wlc_channel.send(await self.translate_message(ctx.author, self.cache["messages"]["welcome"], wlc_channel))
        else:
            await wlc_channel.send("No welcome message set.")

        if self.cache["embeds"]["welcome"] is not None and self.cache["embeds"]["welcome"] != {}:
            wlc_embed = copy.deepcopy(self.cache["embeds"]["welcome"])
            try:
                wlc_embed["title"] = await self.translate_message(ctx.author, wlc_embed["title"], wlc_channel)
            except KeyError:
                pass
            
            try:
                wlc_embed["description"] = await self.translate_message(ctx.author, wlc_embed["description"], wlc_channel)
            except KeyError:
                pass

            await wlc_channel.send(embed=await self.json_to_embed(wlc_embed))
        else:
            await wlc_channel.send("No welcome embed set.")

        if self.cache["messages"]["farewell"] is not None and self.cache["messages"]["farewell"] != "":
            await frw_channel.send(await self.translate_message(ctx.author, self.cache["messages"]["farewell"], frw_channel))
        else:
            await frw_channel.send("No farewell message set.")

        if self.cache["embeds"]["farewell"] is not None and self.cache["embeds"]["farewell"] != {}:
            frw_embed = copy.deepcopy(self.cache["embeds"]["farewell"])

            try:
                frw_embed["title"] = await self.translate_message(ctx.author, frw_embed["title"], frw_channel)
            except KeyError:
                pass

            try:
                frw_embed["description"] = await self.translate_message(ctx.author, frw_embed["description"], frw_channel)
            except KeyError:
                pass

            await frw_channel.send(embed=await self.json_to_embed(frw_embed))
        else:
            await frw_channel.send("No farewell embed set.")

        embed = discord.Embed(
            title="Success", description="Test has finished", colour=Colour.green())

        await ctx.respond(embed=embed)

    @_chn.command(name="set")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def chn_set(self, ctx,
                      channel: discord.Option
                      (str, "The channel you want to set.",
                       choices=[discord.OptionChoice("Welcome Channel", "welcome"), discord.OptionChoice("Farewell Channel", "farewell")]),
                      channel_name: discord.Option(discord.TextChannel, "The channel name you want to set as the events receiver. e.g. #Welcome")):
        """
        Sets the channels for the welcome/farewell messages.

        """

        self.cache["channels"][channel] = channel_name.id

        await self.update_db()

        embed = discord.Embed(
            title="Success",
            description=f"New {channel} channel set! \n{channel_name.mention}", colour=Colour.green())

        await ctx.respond(embed=embed)

    @_chn.command(name="clear", description="Clears the channel of the specified event.")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def chn_clear(self, ctx, channel: discord.Option
                        (str, "The channel you want to set.",
                         choices=[discord.OptionChoice("Welcome Channel", "welcome"),
                                  discord.OptionChoice(
                                      "Farewell Channel", "farewell"),
                                  discord.OptionChoice("Both Channels", "both")]),):
        """
        Clears the channels for the welcome/farewell messages.

        """

        if channel == "both":
            self.cache["channels"]["welcome"] = ""
            self.cache["channels"]["farewell"] = ""
        else:
            self.cache["channels"][channel] = ""

        await self.update_db()

        embed = discord.Embed(
            title="Success", description=f"Channel{'s' if channel == 'both' else ''} cleared!", colour=Colour.green())

        await ctx.respond(embed=embed)

    @_chn.command(name="list", description="Lists the channels set.")
    @checks.has_permissions(PermissionLevel.MOD)
    async def chn_list(self, ctx):
        """
        Lists the channels you set for join/leave events.

        """

        wlc_channel = await self.guild.fetch_channel(int(self.cache["channels"]["welcome"]))
        frw_channel = await self.guild.fetch_channel(int(self.cache["channels"]["farewell"]))

        embed = discord.Embed(
            title="Channels", description=f"Welcome channel: {wlc_channel.mention}!\n Farewell channel: {frw_channel.mention}!", colour=Colour.blue())

        await ctx.respond(embed=embed)

    @_msg.command(name="set", description="Sets the message for the event.")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _msg_set(self, ctx, event: discord.Option
                       (str, "The event for which you wish to set a message for.",
                        choices=[discord.OptionChoice("Welcome", "welcome"), discord.OptionChoice("Farewell", "farewell")]),
                       message: discord.Option(str, "The message you wish to send on a new event.")):
        """
        Sets a new message for a join/leave event.
        
        """

        self.cache["messages"][event] = message

        await self.update_db()

        embed = discord.Embed(
            title="Success", description=f"New {event} event message set.", colour=Colour.green())

        await ctx.respond(embed=embed)

    @_msg.command(name="clear", description="Clears the message for the event.")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _msg_clear(self, ctx, event: discord.Option
                         (str, "The event for which you wish to set a message for.",
                          choices=[discord.OptionChoice("Welcome", "welcome"), discord.OptionChoice("Farewell", "farewell")])):
        """
        Clears a message for a join/leave event.
        
        """

        self.cache["messages"][event] = ""

        await self.update_db()

        embed = discord.Embed(
            title="Success", description=f"Cleared {event} event message.", colour=Colour.green())

        await ctx.respond(embed=embed)

    @_emb.command(name="set", description="Sets the embed for the event.")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _emb_set(self, ctx, event: discord.Option
                       (str, "The event for which you wish to set an embed for.",
                        choices=[discord.OptionChoice("Welcome", "welcome"), discord.OptionChoice("Farewell", "farewell")]),
                       embed: discord.Option(str, "The embed url you wish to send on a new event.")):
        """
        Sets a new embed for a join/leave event.
        
        """

        self.cache["embeds"][event] = await self.pastebin_to_json(embed)

        await self.update_db()

        embed = discord.Embed(
            title="Success", description=f"New {event} event embed set.", colour=Colour.green())

        await ctx.respond(embed=embed)

    @_emb.command(name="clear", description="Clears the embed for the event.")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _emb_clear(self, ctx, event: discord.Option
                         (str, "The event for which you wish to set an embed for.",
                          choices=[discord.OptionChoice("Welcome", "welcome"), discord.OptionChoice("Farewell", "farewell")])):
        """
       Clears an embed for a join/leave event.
        
        """

        self.cache["embeds"][event] = ""

        await self.update_db()

        embed = discord.Embed(
            title="Success", description=f"Cleared {event} event embed.", colour=Colour.green())

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Salute(bot))
