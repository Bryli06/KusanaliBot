import discord
from discord.ext import commands

from core.models import PermissionLevel
from core import checks

import re
import requests

import copy


class Salute(commands.Cog):
    _id = "salute"

    default_cache = {
        "channels": {
            "wlcChannel": "",
            "frwChannel": ""
        },
        "messages": {
            "wlcMessage": "",
            "frwMessage": ""
        },
        "embeds": {
            "wlcEmbed": {},
            "frwEmbed": {}
        }
    }

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.api.get_plugin_partition(self)
        self.cache = {}

        self.bot.loop.create_task(self.load_cache())

    async def update_db(self):  # updates database with cache
        await self.db.find_one_and_update(
            {"_id": self._id},
            {"$set": self.cache},
            upsert=True,
        )

    async def load_cache(self):
        await self.bot.wait_for_connected()

        db = await self.db.find_one({"_id": self._id})
        if db == None:
            db = self.default_cache

        self.cache = db

    async def get_channel_ids(self, arg):
        regex = r"(?<=<#)\d*"

        return re.findall(regex, arg)

    async def translate_message(self, memeber: discord.Member, message, channel: discord.TextChannel):
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
        regex = r"(?<=com/)"
        url = re.sub(regex, "raw/", url)

        json_file = requests.get(url).json()

        return json_file

    async def json_to_embed(self, json_file):
        return discord.Embed.from_dict(json_file)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel: discord.TextChannel = self.bot.get_channel(
            int(self.cache["channels"]["wlcChannel"]))

        if self.cache["messages"]["wlcMessage"] is not None and self.cache["messages"]["wlcMessage"] != "":
            await channel.send(await self.translate_message(member, self.cache["messages"]["wlcMessage"], channel))

        if self.cache["embeds"]["wlcEmbed"] is not None and self.cache["embeds"]["wlcEmbed"] != "":
            wlc_embed = copy.deepcopy(self.cache["embeds"]["wlcEmbed"])
            wlc_embed["description"] = await self.translate_message(member, wlc_embed["description"], channel)
            
            await channel.send(embed=await self.json_to_embed(wlc_embed))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel: discord.TextChannel = self.bot.get_channel(
            int(self.cache["channels"]["frwChannel"]))

        if self.cache["messages"]["frwMessage"] is not None and self.cache["messages"]["frwMessage"] != "":
            await channel.send(await self.translate_message(member, self.cache["messages"]["frwMessage"], channel))

        if self.cache["embeds"]["frwEmbed"] is not None and self.cache["embeds"]["frwEmbed"] != "":
            frw_embed = copy.deepcopy(self.cache["embeds"]["frwEmbed"])
            frw_embed["description"] = await self.translate_message(member, frw_embed["description"], channel)
            
            await channel.send(embed=await self.json_to_embed(frw_embed))

    @commands.group(name="salute", aliases=['slt'], invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _slt(self, ctx):
        """
        Manages welcome/farewell messages.

        You will first need to set the channels the messages will be sent to:
        - `{prefix}slt chn set welcome_channel farewell_channel`

        You might also want to set new welcome/farewell messages:
        - `{prefix}slt wlc msg set welcome_message`
        - `{prefix}slt frw msg set welcome_farewell`

        """

        return await ctx.send_help("salute")

    @_slt.group(name="welcome", aliases=['wlc'], invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _wlc(self, ctx):
        """
        Contains commands to manage welcome messages.

        """

        return await ctx.send_help("salute welcome")

    @_slt.group(name="farewell", aliases=['frw'], invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _frw(self, ctx):
        """
        Contains commands to manage farewell messages.

        """

        return await ctx.send_help("salute farewell")

    @_slt.group(name="channels", aliases=['chn'], invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _chn(self, ctx):
        """
        Includes commands for managing the welcome/farewell channels.

        """

        return await ctx.send_help("salute channels")

    @_wlc.group(name="message", aliases=['msg'], invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _wlc_msg(self, ctx):
        """
        Includes commands for managing the welcome messages.

        """

        return await ctx.send_help("salute welcome message")

    @_wlc.group(name="embed", aliases=['emb'], invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _wlc_emb(self, ctx):
        """
        Includes commands for managing the welcome embeds.

        """

        return await ctx.send_help("salute welcome embed")

    @_frw.group(name="message", aliases=['msg'], invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _frw_msg(self, ctx):
        """
        Includes commands for managing the farewell messages.

        """

        return await ctx.send_help("salute farewell message")

    @_frw.group(name="embed", aliases=['emb'], invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _frw_emb(self, ctx):
        """
        Includes commands for managing the farewell embeds.

        """

        return await ctx.send_help("salute farewell embed")

    @_slt.command(name="test")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def slt_test(self, ctx):
        """
        Sends test welcome/farewell messages in the designated channels.

        """

        wlc_channel: discord.TextChannel = self.bot.get_channel(
            int(self.cache["channels"]["wlcChannel"]))
        frw_channel: discord.TextChannel = self.bot.get_channel(
            int(self.cache["channels"]["frwChannel"]))

        if self.cache["messages"]["wlcMessage"] is not None and self.cache["messages"]["wlcMessage"] != "":
            await wlc_channel.send(await self.translate_message(ctx.author, self.cache["messages"]["wlcMessage"], wlc_channel))
        else:
            await wlc_channel.send("No welcome message set.")

        if self.cache["embeds"]["wlcEmbed"] is not None and self.cache["embeds"]["wlcEmbed"] != "":
            wlc_embed = copy.deepcopy(self.cache["embeds"]["wlcEmbed"])
            wlc_embed["description"] = await self.translate_message(ctx.author, wlc_embed["description"], wlc_channel)

            await wlc_channel.send(embed=await self.json_to_embed(wlc_embed))
        else:
            await wlc_channel.send("No welcome embed set.")

        if self.cache["messages"]["frwMessage"] is not None and self.cache["messages"]["frwMessage"] != "":
            await frw_channel.send(await self.translate_message(ctx.author, self.cache["messages"]["frwMessage"], frw_channel))
        else:
            await frw_channel.send("No farewell message set.")

        if self.cache["embeds"]["frwEmbed"] is not None and self.cache["embeds"]["frwEmbed"] != "":
            frw_embed = copy.deepcopy(self.cache["embeds"]["frwEmbed"])
            frw_embed["description"] = await self.translate_message(ctx.author, frw_embed["description"], frw_channel)
            
            await frw_channel.send(embed=await self.json_to_embed(frw_embed))
        else:
            await frw_channel.send("No farewell embed set.")

    @_chn.command(name="set")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def chn_set(self, ctx, welcome_channel: discord.TextChannel, farewell_channel: discord.TextChannel):
        """
        Sets the channels for the welcome/farewell messages.

        """

        self.cache["channels"]["wlcChannel"] = welcome_channel.id
        self.cache["channels"]["frwChannel"] = farewell_channel.id

        await self.chn_list(ctx)

        await self.update_db()
        await ctx.send("New channels set.")

    @_chn.command(name="clear")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def chn_clear(self, ctx):
        """
        Clears the channels for the welcome/farewell messages.

        """

        self.cache["channels"]["wlcChannel"] = ""
        self.cache["channels"]["frwChannel"] = ""

        await self.update_db()
        await ctx.send("Channels cleared.")

    @_chn.command(name="list")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def chn_list(self, ctx):
        """
        Lists the channels you set for welcome/farewell messages.

        """
        
        await ctx.send("Welcome channel: " + self.bot.get_channel(int(self.cache["channels"]["wlcChannel"])).mention+ "!")
        await ctx.send("Farewell channel: " + self.bot.get_channel(int(self.cache["channels"]["frwChannel"])).mention + "!")

    @_wlc_msg.command(name="set")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def wlc_msg_set(self, ctx, *, message):
        """
        Sets the welcome message.

        The command syntax:
        -`{prefix}slt wlc msg set welcome_message`

        Available blocks:
        -`{{mention}}: mentions the user`
        -`{{user}}: writes the user's name`
        -`{{channel}}: mentions the current channel`
        
        """

        self.cache["messages"]["wlcMessage"] = message

        await self.update_db()
        await ctx.send("New welcome message set.")

    @_wlc_msg.command(name="clear")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def wlc_msg_clear(self, ctx):
        """
        Clears the welcome message.
        
        """

        self.cache["messages"]["wlcMessage"] = ""

        await self.update_db()
        await ctx.send("Welcome message cleared.")


    @_wlc_emb.command(name="set")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def wlc_emb_set(self, ctx, url):
        """
        Sets the welcome embed.

        The command syntax:
        -`{prefix}slt wlc emb set pastebin_url`

        Available blocks:
        -`{{mention}}: mentions the user`
        -`{{user}}: writes the user's name`
        -`{{channel}}: mentions the current channel`
        
        """

        self.cache["embeds"]["wlcEmbed"] = await self.pastebin_to_json(url)

        await self.update_db()
        await ctx.send("New welcome embed set.")

    @_wlc_emb.command(name="clear")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def wlc_emb_clear(self, ctx):
        """
        Clears the welcome embed.
        
        """

        self.cache["embeds"]["wlcEmbed"] = ""

        await self.update_db()
        await ctx.send("Welcome embed cleared.")

    @_frw_msg.command(name="set")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def frw_msg_set(self, ctx, *, message):
        """
        Sets the farewell message.

        The command syntax:
        -`{prefix}slt frw msg set farewell_message`

        Available blocks:
        -`{{mention}}: mentions the user`
        -`{{user}}: writes the user's name`
        -`{{channel}}: mentions the current channel`
        
        """

        self.cache["messages"]["frwMessage"] = message

        await self.update_db()
        await ctx.send("New farewell message set.")

    @_frw_msg.command(name="clear")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def frw_msg_clear(self, ctx):
        """
        Clears the farewell message.
        
        """

        self.cache["messages"]["frwMessage"] = ""

        await self.update_db()
        await ctx.send("Farewell message cleared.")


    @_frw_emb.command(name="set")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def frw_emb_set(self, ctx, url):
        """
        Sets the farewell embed.

        The command syntax:
        -`{prefix}slt frw msg set pastebin_url`

        Available blocks:
        -`{{mention}}: mentions the user`
        -`{{user}}: writes the user's name`
        -`{{channel}}: mentions the current channel`
        
        """

        self.cache["embeds"]["frwEmbed"] = await self.pastebin_to_json(url)

        await self.update_db()
        await ctx.send("New farewell embed set.")

    @_frw_emb.command(name="clear")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def frw_emb_clear(self, ctx):
        """
        Clears the farewell embed.

        """

        self.cache["embeds"]["frwEmbed"] = ""

        await self.update_db()
        await ctx.send("Farewell embed cleared.")

# test
def setup(bot):
    bot.add_cog(Salute(bot))
