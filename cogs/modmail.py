from datetime import datetime
import discord
import re
import hashlib
from enum import Enum
from base64 import b64encode
from discord.ext import commands

from discord import ApplicationContext, Colour, Permissions

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel


class Source(Enum):
    DM = 0
    CHANNEL = 1

class Modmail(BaseCog):
    _id = "modmail"

    _modmail_channel_id = 975554256138534942
    _modmail_role_id = 975558400991707136 

    default_cache = {
        "modmail_channel_id": None,

        "modmail_role_id": None,

        "active": {},

        "archive": {},
    }
    '''

    {
        id: modmail
        active, dict -> dict of all active modmail; {user_id: hash}
        archive, dict -> 
    }

    {
        id, str -> hash of id + title
        user, int -> id of the modmail user
        channel, int -> id of the thread
        messages -> array of the messages. [message: str, author_id: int, dm_message_id, channel_message_id] 
    }
    '''
    async def load_cache(self): #each countdown gets its own document
        cursor = self.db.find({ })
        docs = await cursor.to_list(length=10) #how many documents to buffer shouldn't be too high
        while docs:
            for document in docs:
                _id = document.pop("_id")
                self.cache[_id] = document

            docs = await cursor.to_list(length=10)
            
        main_document = await self.db.find_one({"_id": self._id})
        update = True

        if main_document is None:
            main_document = self.default_cache
        elif main_document.keys() != self.default_cache.keys(): # if the cache in the database has missing keys add them
            main_document = self.default_cache | main_document
        else:
            update = False

        self.cache[self._id] = main_document

        if update:
            await self.update_db(self._id)

        
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

    async def after_load(self):
        self.modmail_channel = await self.guild.fetch_channel(self._modmail_channel_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild != None:
            return

        if str(message.author.id) not in self.cache[self._id]["active"]:
            embed = discord.Embed(
                description="If you wish to start a modmail thread please use `/start`\nFor ending an active thread please use `/end`", colour=Colour.blue())

            dm_channel = await message.author.create_dm()
            await dm_channel.send(embed=embed)

            return
        
        thread_hash = self.cache[self._id]["active"][str(message.author.id)]
        thread = await self.guild.fetch_channel(
            self.cache[thread_hash]["channel"])

        embed = discord.Embed(description=message.content,
                              timestamp=datetime.now(), colour=Colour.green())
        embed.set_author(
            name=f"{message.author.name}#{message.author.discriminator}", icon_url=message.author.avatar)
        
        channel_message = await thread.send(embed=embed)

        self.cache[thread_hash]["messages"].append({"message": message.content, 
                                                    "author": message.author.id, 
                                                    "dm_message": message.id,
                                                    "channel_message": channel_message.id, 
                                                    "source": Source.DM.value
                                                    })

        await self.update_db(thread_hash)

        await message.add_reaction('✅')

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.guild != None:
            return
        
        if str(before.author.id) not in self.cache[self._id]["active"]:
            return
        
        thread_hash = self.cache[self._id]["active"][str(before.author.id)]

        for message in self.cache[thread_hash]["messages"]:
            if before.id == message["dm_message"]:
                thread = await self.guild.fetch_channel(self.cache[thread_hash]["channel"])

                _message = await thread.fetch_message(message["channel_message"])

                embed = _message.embeds[0]

                embed.description = f"**Original** \n {embed.description} \n\n **Edited**\n {after.content}"
                embed.title = "Message Edited"
                embed.colour = Colour.blue()

                await _message.edit(embed=embed)

                message["edited_message"] = after.content

                await self.update_db(thread_hash)

                return

                
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or message.guild != None:
            return
        
        if str(message.author.id) not in self.cache[self._id]["active"]:
            return
        
        thread_hash = self.cache[self._id]["active"][str(message.author.id)]

        for _message in self.cache[thread_hash]["messages"]:
            if message.id == _message["dm_message"]:
                thread = await self.guild.fetch_channel(self.cache[thread_hash]["channel"])

                thread_message = await thread.fetch_message(_message["channel_message"])
                
                embed = thread_message.embeds[0]

                embed.title = "Message Deleted"
                embed.colour = Colour.red()

                await thread_message.edit(embed=embed)

                _message["deleted_message"] = _message["message"]

                await self.update_db(thread_hash)

                return

    # check if the user is ending the session
    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        thread_hash = self.hash(thread.name)
        if self.cache[thread_hash]["ended"]:
            return

        user = self.cache[thread_hash]["user"]

        self.cache[self._id]["archive"].setdefault(str(user), []).append(thread_hash)

        await self.update_db(self._id)

        self.cache[thread_hash]["ended"] = True

        await self.update_db(thread_hash)
        
        member = await self.guild.fetch_member(user)
        
        await member.send("Session was closed by staff.")

    @commands.Cog.listener()
    async def on_thread_remove(self, thread):
        thread_hash = self.hash(thread.name)
        if self.cache[thread_hash]["ended"]:
            return

        user = self.cache[thread_hash]["user"]

        self.cache[self._id]["archive"].setdefault(str(user), []).append(thread_hash)

        await self.update_db(self._id)

        self.cache[thread_hash]["ended"] = True

        await self.update_db(thread_hash)
        
        member = await self.guild.fetch_member(user)
        
        await member.send("Session was closed by staff.")

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        before_hash = self.hash(before.name)
        if self.cache[before_hash]["ended"]:
            return

        if after.name != before.name:
            after_hash = self.hash(after.name)
            self.cache[after_hash] = self.cache.pop(before_hash)
            
            await self.update_db(after_hash)
            await self.update_db(before_hash)

        if after.archived == False and before.id == after.id:
            return
        
        user = self.cache[before_hash]["user"]

        self.cache[self._id]["archive"].setdefault(str(user), []).append(before_hash)

        await self.update_db(self._id)

        self.cache[before_hash]["ended"] = True

        await self.update_db(before_hash)
        
        member = await self.guild.fetch_member(user)
        
        await member.send("Session was closed by staff.")


    @commands.slash_command(name="reply", description="Replies to a user in a modmail thread.", default_member_permissions=Permissions(manage_threads=True))
    @checks.has_permissions(PermissionLevel.MOD)
    @checks.only_modmail_thread(_modmail_channel_id)
    async def reply(self, ctx: ApplicationContext, message: discord.Option(str, "The message you wish to reply with.")):
        """
        Replies to a modmail thread.

        """
        thread_hash = self.hash(ctx.channel.name)
        
        if self.cache[thread_hash]["ended"]:
            embed = discord.Embed(title="Error",
                                    description="This modmail is already closed", colour=Colour.red())

            await ctx.respond(embed=embed)

            return

        embed = discord.Embed(description=message,
                              timestamp=datetime.now(), colour=Colour.green())
        embed.set_author(
            name=f"{ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.avatar)
        embed.set_footer(text=ctx.author.roles[-1].name)
        
        
        user = self.cache[thread_hash]["user"]
        
        
        member = await self.guild.fetch_member(int(user))

        dm_channel = await member.create_dm()
        dm_message = await dm_channel.send(embed=embed)

        channel_message = await ctx.respond(embed=embed)

        self.cache[thread_hash]["messages"].append({"message": message, 
                                                    "author": ctx.author.id, 
                                                    "dm_message": dm_message.id,
                                                    "channel_message": channel_message.id, 
                                                    "source": Source.CHANNEL.value
                                                    })

        await self.update_db(thread_hash)

    @commands.slash_command(name="delete", description="Delete the most recently sent message in a modmail thread.", default_member_permissions=Permissions(manage_threads=True))
    @checks.has_permissions(PermissionLevel.MOD)
    @checks.only_modmail_thread(_modmail_channel_id)
    async def delete(self, ctx: ApplicationContext):
        """
        Replies to a modmail thread.

        """
        thread_hash = self.hash(ctx.channel.name)
        
        if self.cache[thread_hash]["ended"]:
            embed = discord.Embed(title="Error",
                                    description="This modmail is already closed", colour=Colour.red())

            await ctx.respond(embed=embed)

            return

        for _message in reversed(self.cache[thread_hash]["messages"]):
            if Source.CHANNEL.value == _message["source"]:
                thread = await self.guild.fetch_channel(self.cache[thread_hash]["channel"])
                dm_channel = await self.bot.fetch_user(self.cache[thread_hash]["user"])

                dm_message = await dm_channel.fetch_message(_message["dm_message"])
                
                embed = dm_message.embeds[0]

                embed.title = "Message Deleted"
                embed.colour = Colour.red()

                _message["deleted_message"] = _message["message"]

                await self.update_db(thread_hash)
                
                await dm_message.delete()

                await ctx.respond(embed=embed)

                return


    @commands.slash_command(name="start", description="Starts a modmail session.")
    @commands.dm_only()
    async def start(self, ctx: ApplicationContext, title: discord.Option(str, "The title of the thread."),
                    reason: discord.Option(str, "The reason for starting a modmail sessions.")):
        """
        Starts a new modmail thread. DM only command.

        """

        if str(ctx.author.id) in self.cache[self._id]["active"]:
            await ctx.respond("Session already started.")

            return

        member = await self.guild.fetch_member(ctx.author.id)

        thread: discord.Thread = await self.modmail_channel.create_thread(name=f"{ctx.author.id} — {title}")

        embed = discord.Embed(
            description=f"{ctx.author.mention}\nReason for mail: {reason}", timestamp=datetime.now(), colour=Colour.green())

        embed.set_author(
            name=f"{member.name}#{member.discriminator}", icon_url=member.display_avatar)
        embed.add_field(name="**Nickname**", value=member.display_name)

        value = ""
        for role in member.roles:
            value += f"{role.mention} "

        embed.add_field(name="**Roles**", value=value)

        channel_message = await thread.send(embed=embed)

        await ctx.defer()

        role = await self.guild._fetch_role(self._modmail_role_id)

        async for member in self.guild.fetch_members(limit=None):
            if role in member.roles:
                await thread.add_user(member)

        parsed_owners = re.findall(r"\d{18}", self.bot.config["owners"])
        for owner in parsed_owners:
            member = await self.guild.fetch_member(int(owner))
            await thread.add_user(member)
        
        thread_hash = self.hash(thread.name)

        self.cache[self._id]["active"][str(ctx.author.id)] = thread_hash
        await self.update_db(self._id)

        await ctx.respond("Your message has been sent! Please wait patiently while the staff respond!")

        self.cache[thread_hash] = {
            "user": ctx.author.id,
            "channel": thread.id,
            "title": title,
            "messages": [{
                            "message": reason, 
                            "author": ctx.author.id, 
                            "dm_message": None, 
                            "channel_message": channel_message.id, 
                            "source": Source.DM.value
                        }],
            "ended": False,
        }

        await self.update_db(thread_hash)

    @commands.slash_command(name="end", description="Ends a modmail session.")
    async def end(self, ctx: ApplicationContext):
        """
        Ends an active modmail thread.

        """
        await ctx.defer()

        if ctx.author.bot or not ctx.guild:
            await self.end_from_dm(ctx)

            return

        thread_hash = self.hash(ctx.channel.name)

        author_id = self.cache[thread_hash]["user"]

        if str(author_id) not in self.cache[self._id]["active"]:
            await ctx.respond("No session found.")

            return


        user = self.cache[thread_hash]["channel"]

        thread = await self.guild.fetch_channel(user)

        self.cache[thread_hash]["ended"] = True

        self.cache[self._id]["active"].pop(str(author_id))

        self.cache[self._id]["archive"].setdefault(str(author_id), []).append(thread_hash)

        await self.update_db(self._id)

        self.cache[thread_hash]["ended"] = True

        await self.update_db(thread_hash)

        member = await self.bot.fetch_user(author_id)

        await member.send("Session ended!")
        
        self.bot.loop.call_later(5, self._end, thread)

        await ctx.respond("Session ended!")


    def _end(self, thread):
        return self.bot.loop.create_task(self._end_helper(thread))

    async def _end_helper(self, thread):
        await thread.archive()

    
    async def end_from_dm(self, ctx):
        if str(ctx.author.id) not in self.cache[self._id]["active"]:
            await ctx.respond("No session found.")

            return

        key = self.cache[self._id]["active"][str(ctx.author.id)]
        
        user = self.cache[key]["channel"]

        thread = await self.guild.fetch_channel(user)

        thread_hash = self.cache[self._id]["active"].pop(str(ctx.author.id))

        self.cache[self._id]["archive"].setdefault(str(ctx.author.id), []).append(thread_hash)

        await self.update_db(self._id)

        self.cache[thread_hash]["ended"] = True

        await self.update_db(thread_hash)

        await thread.archive()

        await ctx.respond("Session ended!")


    def hash(self, s: str):
        return b64encode(bytes.fromhex(hashlib.sha224(s.encode()).hexdigest())).decode()[:16] #what the actual fuck


def setup(bot):
    bot.add_cog(Modmail(bot))
