from datetime import datetime
import discord
from discord.ext import commands

from discord import ApplicationContext, Colour, Permissions

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel


class Modmail(BaseCog):
    _id = "modmail"

    _modmail_channel_id = 981271368140206170
    _modmail_role_id = 975558400991707136

    default_cache = {
        "userThreads": {

        }
    }

    async def after_load(self):
        self.modmail_channel = await self.guild.fetch_channel(self._modmail_channel_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild != None:
            return

        if str(message.author.id) not in self.cache["userThreads"]:
            embed = discord.Embed(
                description="If you wish to start a modmail thread please use `/start`\nFor ending an active thread please use `/end`", colour=Colour.blue())

            dm_channel = await message.author.create_dm()
            await dm_channel.send(embed=embed)

            return

        thread = await self.guild.fetch_channel(
            self.cache["userThreads"][str(message.author.id)])

        embed = discord.Embed(description=message.content,
                              timestamp=datetime.now(), colour=Colour.blue())
        embed.set_author(
            name=f"{message.author.name}#{message.author.discriminator}", icon_url=message.author.avatar)

        await thread.send(embed=embed)

    # check if the user is ending the session
    ending = False

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        if self.ending:
            return

        for user in self.cache["userThreads"]:
            if self.cache["userThreads"][user] == thread.id:
                self.cache["userThreads"].pop(user)

                member = await self.guild.fetch_member(int(user))
                await member.send("Session was closed by staff.")

                break

        await self.update_db()

    @commands.Cog.listener()
    async def on_thread_remove(self, thread):
        if self.ending:
            return

        for user in self.cache["userThreads"]:
            if self.cache["userThreads"][user] == thread.id:
                self.cache["userThreads"].pop(user)

                member = await self.guild.fetch_member(int(user))
                await member.send("Session was closed by staff.")

                break

        await self.update_db()

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        if self.ending:
            return

        if after.archived == False and before.id == after.id:
            return

        for user in self.cache["userThreads"]:
            if self.cache["userThreads"][user] == before.id:
                self.cache["userThreads"].pop(user)

                member = await self.guild.fetch_member(int(user))
                await member.send("Session was closed by staff.")

                break

        await self.update_db()

    @commands.slash_command(name="reply", description="Replies to a user in a modmail thread.", default_member_permissions=Permissions(manage_messages=True))
    @checks.has_permissions(PermissionLevel.MOD)
    @checks.only_modmail_thread(_modmail_channel_id)
    async def reply(self, ctx: ApplicationContext, message: discord.Option(str, "The message you wish to reply with.")):
        """
        Replies to a modmail thread.

        """

        embed = discord.Embed(description=message,
                              timestamp=datetime.now(), colour=Colour.blue())
        embed.set_author(
            name=f"{ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.avatar)

        for user in self.cache["userThreads"]:
            if self.cache["userThreads"][user] == ctx.channel.id:
                member = await self.guild.fetch_member(int(user))

                dm_channel = await member.create_dm()
                await dm_channel.send(embed=embed)

        await ctx.respond(embed=embed)

    @commands.slash_command(name="start", description="Starts a modmail session.")
    @commands.dm_only()
    async def start(self, ctx: ApplicationContext, title: discord.Option(str, "The title of the thread."),
                    reason: discord.Option(str, "The reason for starting a modmail sessions.")):
        """
        Starts a new modmail thread. DM only command.

        """

        if str(ctx.author.id) in self.cache["userThreads"]:
            await ctx.respond("Session already started.")

            return

        member = await self.guild.fetch_member(ctx.author.id)

        thread: discord.Thread = await self.modmail_channel.create_thread(name=title)

        embed = discord.Embed(
            description=f"{ctx.author.mention}\nReason for mail: {reason}", timestamp=datetime.now(), colour=Colour.green())

        embed.set_author(
            name=f"{member.name}#{member.discriminator}", icon_url=member.display_avatar)
        embed.add_field(name="**Nickname**", value=member.display_name)

        value = ""
        for role in member.roles:
            value += f"{role.mention} "

        embed.add_field(name="**Roles**", value=value)

        await thread.send(embed=embed)

        await ctx.defer()

        role = await self.guild._fetch_role(self._modmail_role_id)

        async for member in self.guild.fetch_members(limit=None):
            if role in member.roles:
                await thread.add_user(member)

        self.cache["userThreads"].update({str(ctx.author.id): thread.id})
        await self.update_db()

        await ctx.respond("Session started!")

    @commands.slash_command(name="end", description="Ends a modmail session.")
    @commands.dm_only()
    async def end(self, ctx: ApplicationContext):
        """
        Ends an active modmail thread.

        """

        if str(ctx.author.id) not in self.cache["userThreads"]:
            await ctx.respond("No session found.")

            return

        self.ending = True

        thread = await self.guild.fetch_channel(
            self.cache["userThreads"][str(ctx.author.id)])

        await thread.archive()

        self.cache["userThreads"].pop(str(ctx.author.id))
        await self.update_db()

        await ctx.respond("Session ended!")

        self.ending = False


def setup(bot):
    bot.add_cog(Modmail(bot))
