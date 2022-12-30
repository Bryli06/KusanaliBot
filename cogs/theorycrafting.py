import discord
from discord.ui import Button, View, Select, Modal, InputText
from discord import ApplicationContext, Colour, SlashCommandGroup, Interaction, TextChannel, OptionChoice, Permissions
from discord.ext import commands

from datetime import datetime
from core import checks
from captcha.image import ImageCaptcha
import shlex
import string
import hashlib
from base64 import b64encode
import random
import re

from core.time import TimeConverter, InvalidTime
from core.base_cog import BaseCog
from core.checks import PermissionLevel
from core.ui import captcha_modal
from core.context import ModContext

class Theorycrafting(BaseCog):
    _id="theorycrafting"
    
    default_cache={
        "active": [],
        "archive": [],
        "log": None,
        "unmute_queue": {},
    }
    
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
        
        await self.bot.increment_tasks()


    async def update_db(self, _id): #we need a different insert command that allows us to insert into seperate documents
        if _id not in self.cache:
            await self.db.delete_one({"_id": _id})
            return

        await self.db.find_one_and_update(
            {"_id": _id},
            {"$set": self.cache[_id]},
            upsert=True,
        )

    _lgr = SlashCommandGroup("logger", "Commands regarding the logger", )
    _tc = SlashCommandGroup("theorycrafting", "Commands specific for theorycrafting")


    async def after_load(self):
        for message_id in self.cache[self._id]["active"]:
            await self.start_vote(message_id)
            if "end" in self.cache[message_id]:
                await self._end(message_id, self.cache[message_id]["end"])

        for k, v in list(self.cache[self._id]["unmute_queue"].items()):
            await self._unmute(k, v)
        

    @commands.slash_command(name="idp", description="It depends")
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def idp(self, ctx: ApplicationContext):
        description = ("*Depends on characters*\n"
                    "*Depends on constellations*\n"
                    "*Depends on weapons*\n"
                    "*Depends on substats*\n"
                    "*Depends on team comps*\n"
                    "*Depends on your PC*\n"
                    "*Depends on your Wifi*\n"
                    "*Depends on the current moon phase*\n"
                    "*Depends on the brand of cereal Biden ate today*\n"
                    "*Depends on the number of chocolate chips in Liu Wei’s cookie*\n"
                    "*Depends on the moles of oxygen in the air*\n"
                    "*Depends on your distance from a blackhole*\n"
                    "*Depends on the number of hairs you have over 2.21 mm long*\n"
                    "*Depends on the hydration levels in the pee of a guy named Darmo Kasim in Indonesia*\n"
                    "*Depends on if P = NP*\n"
                    "*Depends on if Drak can finally 36\\**\n\n"
                    "**It Depends™**")
        embed = discord.Embed(title="It Depends.", description=description, colour=Colour.red())

        await ctx.respond(embed=embed)

    @_lgr.command(name="parser", description="Parses logs")
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def parser(self, ctx: ApplicationContext):
        description = "Paste your logs into the Parser category on A:A in [this spreadsheet](https://docs.google.com/spreadsheets/d/1bVVG-w6F-L0YOdFbaT8iOmv-p3lZl6m3SBCjeY2PWbw/edit?usp=sharing)"

        embed = discord.Embed(title="Parser", description=description, colour=Colour.blue())

        await ctx.respond(embed=embed)

    @_lgr.command(name="help", description="Explains how to use logger")
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def helper(self, ctx: ApplicationContext):
        pass

    _vote = _tc.create_subgroup(name="vote", description="commands for managing tc polls")

    @_vote.command(name="create", description="create an anonymous poll with options")
    @checks.has_permissions(PermissionLevel.TC_ADMIN)
    async def vote_create(self, ctx: ApplicationContext, title: discord.Option(str, "Title of the poll"), 
            description: discord.Option(str, "Description of the poll"), options: discord.Option(str, "Options members can vote for"), 
            max_selections: discord.Option(int, min_value=1, description="Max number of options users can pick", default=-1),
            duration: discord.Option(str, "Duration of poll", default="inf")):
        
        await ctx.defer(ephemeral=True)
        
        after = None
        if duration != "inf":
            try:
                after = TimeConverter(duration)

            except InvalidTime as e:
                embed = discord.Embed(
                    title="Error", description=e, colour=Colour.red())
                await ctx.respond(embed=embed)

                return

        options = shlex.split(options)

        if max_selections == -1:
            max_selections = len(options)

        description = f"{description}\n"
        c = 'A'
        for option in options:
            description+=f"\n{c}: {option}"
            c = chr(ord(c)+1) # who uses iterators in python ew

        embed = discord.Embed(title=title, description=description, color=Colour.blue())

        options = dict.fromkeys(options + ['Abstain'], 0)

        class confirmButton(discord.ui.Button):
            def __init__(self, cog):
                self.cog = cog

                super().__init__(
                    label="✅", 
                    style=discord.ButtonStyle.green
                )

            async def callback(self, interaction: Interaction):
                for child in self.view.children:
                    child.disabled = True
            
                message = await ctx.channel.send(embed=embed)

                self.cog.cache[message.id] = {
                    "title": title,
                    "channel": ctx.channel.id, 
                    "options": options,
                    "voters": {},
                    "selections": max_selections,
                }

                if after:
                    self.cog.cache[message.id]["end"] = after.final.timestamp()
                    await self.cog._end(message.id, after.final.timestamp())
                    

                self.cog.cache[self.cog._id]["active"].append(message.id)

                await self.cog.update_db(message.id)
                await self.cog.update_db(self.cog._id)

                await self.cog.start_vote(message.id)
            
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


    async def _end(self, messageid, time):
        end = datetime.fromtimestamp(int(time))
        now = datetime.now()
        closetime = (end - now).total_seconds() if time else 0

        if closetime > 0:
            self.bot.loop.call_later(closetime, self._end_after, messageid)
        else:
            await self._end_helper(messageid)

        
    async def _end_helper(self, messageid):
        if messageid not in self.cache[self._id]["active"]:
            return

        self.cache[self._id]["active"].remove(messageid)
        self.cache[self._id]["archive"].append(messageid)

        await self.update_db(self._id)
        message = await self.get_message_from_id(messageid)

        embed = message.embeds[0]
        embed.description = f"{embed.description}\n\n__Results:__{self.get_results(messageid)}"
        embed.colour = Colour.red()

        await message.edit(embed=embed, view=None)

        embed = discord.Embed(title="Vote ended", description=f"Vote for {self.cache[messageid]['title']} automatically ended.")
        
        if self.cache[self._id]["log"]:
            chn = await self.guild.fetch_channel(self.cache[self._id]["log"])

            await chn.send(embed=embed)

        
        
        
    def _end_after(self, messageid):
        return self.bot.loop.create_task(self._end_helper(messageid))

    @_vote.command(name="end", description="ends an existing vote")
    @checks.has_permissions(PermissionLevel.TC_ADMIN)
    async def vote_end(self, ctx: ApplicationContext):

        if not self.cache[self._id]["active"]:
            embed = discord.Embed(title="Error", description="No active votes.", colour=Colour.red())

            await ctx.respond(embed=embed)
            return

        options = []
        for i, vote in enumerate(self.cache[self._id]["active"]):
            options.append(discord.SelectOption(
                label=self.cache[vote]["title"],
                value=str(i),
                ))
        select = Select(
            placeholder="Select which vote to end",
            options=options,
            )

        async def _select_callback(interaction: Interaction):
            message_id = self.cache[self._id]["active"].pop(int(select.values[0]))
            self.cache[self._id]["archive"].append(message_id)

            await self.update_db(self._id)
            message = await self.get_message_from_id(message_id)

            embed = message.embeds[0]
            embed.description = f"{embed.description}\n\n__Results:__{self.get_results(message_id)}"
            embed.colour = Colour.red()

            await message.edit(embed=embed, view=None)

            embed = discord.Embed(title="Report", description="Successfully ended vote and results shown.")

            await interaction.response.send_message(embed=embed)

            embed = discord.Embed(title="Vote ended", description=f"Vote for {self.cache[message_id]['title']} ended by {ctx.author.mention}.")

            if self.cache[self._id]["log"]:
                chn = await self.guild.fetch_channel(self.cache[self._id]["log"])

                await chn.send(embed=embed)


        select.callback = _select_callback

        view = View(select, timeout=60)
        await ctx.respond(view=view, ephemeral=True)


    async def add_buttons(self, message: discord.Message):
        async def abstain_callback(interaction: Interaction):
            poll = self.cache[message.id]

            user_id = hash(str(interaction.user.id))

            if user_id in poll["voters"]:
                old = poll["voters"][user_id]
                poll["voters"][user_id] = ["Abstain"]

                for vote in old:
                    if vote == "Abstain":
                        poll["options"]['Abstain'] -= 1
                        continue

                    poll['options'][list(poll['options'])[ord(vote)-ord('A')]] -= 1


                poll["options"]['Abstain'] += 1

                await self.update_db(message.id)

                embed = discord.Embed(
                        title="Report", description=f"Switched votes from {list_to_string(old)} to Abstain",
                        colour=Colour.green())
                
                await self.vote_log(interaction.user, f"switched votes from {list_to_string(old)} to Abstain.")

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return


            poll["voters"][user_id] = ["Abstain"]
            
            poll["options"]['Abstain'] += 1
            
            await self.update_db(message.id)

            embed = message.embeds[0]
            embed.title = f"{poll['title']} ({len(poll['voters'])} voted)"

            await message.edit(embed=embed)
            
            embed = discord.Embed(title="Report", description=f"Successfully voted for Abstain.", colour=Colour.green())
            await self.vote_log(interaction.user, "voted for Abstain.") 

            await interaction.response.send_message(embed=embed, ephemeral=True)



        async def results_callback(interaction: Interaction):
            poll = self.cache[message.id]

            user_id = hash(str(interaction.user.id))

            if user_id in poll["voters"]:
                embed = discord.Embed(title="Report", description=f"You voted for {list_to_string(poll['voters'][user_id])}\n\n__Results:__{self.get_results(message.id)}")

                await self.results_log(interaction.user)

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            embed = discord.Embed(title="Error", description="You must vote before you can view the results.", colour=Colour.green())

            await self.results_error_log(interaction.user)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        
        abstain = Button(label="✨ABSTAIN✨", style=discord.ButtonStyle.blurple)
        abstain.callback = abstain_callback

        vote = Button(label="vote", style=discord.ButtonStyle.gray)
        vote.callback = self.get_captcha_callback(message)

        results = Button(label="results", style=discord.ButtonStyle.gray)
        results.callback = results_callback

        view = View(abstain, vote, results, timeout=None)

        await message.edit(view=view)
    
    def get_captcha_callback(self, message):
        async def captcha(interaction: Interaction):
            image = ImageCaptcha(width=280, height=90, fonts=['./fonts/captcha.ttf'])
            text = string_generator()
            data = image.generate(text)
            data.seek(0)
            file = discord.File(fp=data, filename="image.png")


            embed = discord.Embed(title="Please verify yourself before you vote.",
                                description="Once you are ready to provide your answer click the button below.\n\n **NOTE:** The captcha only consists of lowercase letters, numbers, and does not inclue spaces.", colour=Colour.blue())

            embed.set_image(url="attachment://image.png")

            answer = Button(label="Answer", style=discord.ButtonStyle.blurple)

            view = View(answer, timeout=60)

            next_view = self.get_vote_view(message)

            async def _answer_callback(interaction: discord.Interaction):
                await interaction.response.send_modal(captcha_modal(self, text, view, interaction, next_view))

            answer.callback = _answer_callback

            await interaction.response.send_message(embed=embed, file=file, view=view, ephemeral=True)

        return captcha

    def get_vote_view(self, message):
        options = []
        c = 'A'
        for option in self.cache[message.id]["options"]:
            if option == 'Abstain':
                continue

            options.append(discord.SelectOption(
                label=c,
                value=c,
                description=option
            ))
            c = chr(ord(c)+1)

        vote = Select(
            placeholder="Select choices",
            max_values=self.cache[message.id]["selections"],
            options=options
        )

        vote.callback = self.vote_callback(message, vote)

        return View(vote)

    def vote_callback(self, message, votes):
        async def _callback(interaction: Interaction):
            poll = self.cache[message.id]

            user_id = hash(str(interaction.user.id))

            if user_id in poll["voters"]:
                old = poll["voters"][user_id]
                poll["voters"][user_id] = votes.values

                for vote in old:
                    if vote == "Abstain":
                        poll["options"]['Abstain'] -= 1
                        continue

                    poll['options'][list(poll['options'])[ord(vote)-ord('A')]] -= 1


                for vote in poll["voters"][user_id]:
                    if vote == "Abstain":
                        poll["options"]['Abstain'] += 1
                        continue

                    poll['options'][list(poll['options'])[ord(vote)-ord('A')]] += 1 #please kms if this doesn't work

                await self.update_db(message.id)

                embed = discord.Embed(
                        title="Report", description=f"Switched votes from {list_to_string(old)} to {list_to_string(votes.values)}",
                        colour=Colour.green())

                await self.vote_log(interaction.user, f"switched votes from {list_to_string(old)} to {list_to_string(votes.values)}.")

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return


            poll["voters"][user_id] = votes.values
            
            for vote in poll["voters"][user_id]:
                if vote == "Abstain":
                    poll["options"]['Abstain'] += 1
                    continue

                poll['options'][list(poll['options'])[ord(vote)-ord('A')]] += 1 
            
            await self.update_db(message.id)

            embed = message.embeds[0]
            embed.title = f"{poll['title']} ({len(poll['voters'])} voted)"

            await message.edit(embed=embed)
            
            embed = discord.Embed(title="Report", description=f"Successfully voted for {list_to_string(votes.values)}.", colour=Colour.green())

            await self.vote_log(interaction.user, f"voted for {list_to_string(votes.values)}.") 

            await interaction.response.send_message(embed=embed, ephemeral=True)

        return _callback


 
    async def start_vote(self, message_id):
        message = await self.get_message_from_id(message_id)

        await self.add_buttons(message)

    async def get_message_from_id(self, message_id):
        channel: TextChannel = await self.guild.fetch_channel(
            self.cache[message_id]["channel"])
        
        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            self.bot.dispatch("error", e,
                              f"There seems to be an active poll in {channel.mention} that the bot cannot access.",
                              f"Delete the poll in {channel.mention} manually `ID: {message_id}`.")

            self.cache.pop(message_id)
            await self.update_db(message_id)

            return None

        return message

    @_vote.command(name="logger", description="sets vote logs") 
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def setlogger(self, ctx: ApplicationContext, channel: discord.Option(discord.TextChannel, "Channel to log to")):
        self.cache[self._id]["log"] = channel.id
        await self.update_db(self._id)
        
        embed = discord.Embed(
            title="Success", description=f"Set logs channel as {channel.mention}.", colour=Colour.green())
        await ctx.respond(embed=embed)



    async def captcha_log(self, member, captcha, answer):
        if captcha != answer:
            embed = discord.Embed(title="Verification attempted", description=f"Member {member.mention}`{member.name}#{member.discriminator}` incorrectly entered captcha. \n\n**Correct Answer:** {answer}\n**Submitted Answer:** {captcha}",
                colour=Colour.red(), timestamp=datetime.now())

        else:
            embed = discord.Embed(title="Verification Successful", description=f"Member {member.mention}`{member.name}#{member.discriminator}` solved the captcha. \n\n**Correct Answer:** {answer}",
                colour=Colour.green(), timestamp=datetime.now())

        if self.cache[self._id]["log"]:
            chn = await self.guild.fetch_channel(self.cache[self._id]["log"])

            await chn.send(embed=embed)



    async def vote_log(self, member, message):
        embed = discord.Embed(title="Member vote changed", description=f"Member {member.mention}`{member.name}#{member.discriminator}` {message}",
                colour=Colour.blue(), timestamp=datetime.now())
        
        if self.cache[self._id]["log"]:
            chn = await self.guild.fetch_channel(self.cache[self._id]["log"])

            await chn.send(embed=embed)

    async def results_log(self, member):
        embed = discord.Embed(title="Member viewed the results", description=f"Member {member.mention}`{member.name}#{member.discriminator}` viewed the results",
                colour=Colour.blue(), timestamp=datetime.now())

        if self.cache[self._id]["log"]:
            chn = await self.guild.fetch_channel(self.cache[self._id]["log"])

            await chn.send(embed=embed)

    async def results_error_log(self, member):
        embed = discord.Embed(title="Member tried to view the results", description=f"Member {member.mention}`{member.name}#{member.discriminator}` tried to view the results but has not voted.",
                colour=Colour.red(), timestamp=datetime.now())

        if self.cache[self._id]["log"]:
            chn = await self.guild.fetch_channel(self.cache[self._id]["log"])

            await chn.send(embed=embed)


    def get_results(self, messageid):
        message = ""

        c = 'A'

        for k, v in self.cache[messageid]["options"].items():
            if k == 'Abstain':
                continue
            message += f"\n**{c}: **{v}"
            c = chr(ord(c)+1)

        message += f"\n**Abstain: **{self.cache[messageid]['options']['Abstain']}"

        return message

#------------------------------ tc mod commands ------------------------------#

    @_tc.command(name="setmute", description="Sets the mute role.")
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

        if "mutes" not in self.cache:
            self.cache["mutes"] = {}

        self.cache["mutes"]["muteRole"] = role.id
        await self.update_db("mutes")

        embed = discord.Embed(
            title="Success", description=f"Successfully set the mute role as {role.mention}", colour=Colour.green())
        await ctx.respond(embed=embed)

    @_tc.command(name="mute", description="Mutes a member")
    @commands.max_concurrency(1, wait=True)
    @checks.has_permissions(PermissionLevel.TRIAL_TC_MOD)
    async def mute(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to mute."),
                   duration: discord.Option(str, description="The duration of the mute.", default="inf"),
                   reason: discord.Option(str, description="Reason for mute.", default="No reason given.")):
        """
        Mutes a member via /mute [members] [duration: Optional] [reason: Optional]

        """
        await ctx.defer()

        if "mutes" not in self.cache:
            self.cache["mutes"] = {}

        if not self.cache["mutes"]["muteRole"]:
            embed = discord.Embed(
                title="Error", description="Please set a mute role first by running `/theorycrafting setmute [role]`", colour=Colour.red())
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

        member_ids = self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        mute_role = await self.guild._fetch_role(self.cache["mutes"]["muteRole"])

        description = ""
        for member_id in member_ids:
            try:
                member: discord.Member = await self.guild.fetch_member(int(member_id))
            except Exception:
                description += f"The member with ID `{member_id}` was not found.\n"
                continue

            if str(ctx.author.id) not in self.bot.config["owners"] and ctx.author.roles[-1] <= member.roles[-1]:
                description += f"You do not have the permission to mute the member {member.mention}.\n"
                continue

            if mute_role in member.roles:
                description += f"The member with ID `{member_id}` is already muted.\n"
                continue

            try:
                await member.add_roles(mute_role, reason=reason)

                description += f"The member {member.mention} `{member.name}#{member.discriminator}` has been successfully muted, "
            except Exception as e:
                self.bot.dispatch("error", e)
                description += f"The member {member.mention} `{member.name}#{member.discriminator}` could not be muted.\n"

                continue

            try:
                dm = await member.create_dm()
                await dm.send(f"You have been TC muted in {self.guild.name}. Reason: {reason}")
                description += "and a message has been sent.\n"
            except:
                self.logger.error(f"Could not message {member.name}.")
                description += "but a message could not be sent.\n"

            if after:
                self.cache[self._id]["unmute_queue"][str(
                    member_id)] = after.final.timestamp()
                await self._unmute(member_id, after.final.timestamp())

            self.cache["mutes"].setdefault(str(member_id), []).append(
                {"responsible": ctx.author.id, "reason": reason, "duration": duration, "time": datetime.now().timestamp(), })

            self.bot.dispatch("member_tc_mute", ModContext(member=member, moderator=ctx.author,
                              reason=reason, timestamp=datetime.now().timestamp(), duration=duration))

        await self.update_db("mutes")
        await self.update_db(self._id)

        if after:
            description += f"Unmuting at <t:{round(after.final.timestamp())}:F>.\n"

        description = self.format_string(description)

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())
        
        new_line = "\n" #limitation of fstring
        embed.set_footer(text=f"Latest {description.count(new_line)} lines shown")
        
        await ctx.respond(embed=embed)


    @_tc.command(name="unmute", description="Unmutes a member.", default_member_permissions=Permissions(manage_messages=True))
    @commands.max_concurrency(1, wait=True)
    @checks.has_permissions(PermissionLevel.TRIAL_TC_MOD)
    async def unmute(self, ctx: ApplicationContext, members: discord.Option(str, description="The members you want to unmute."),
                     reason: discord.Option(str, description="Reason for unmute.", default="No reason given.")):
        """
        Unmutes a member via /unmute [members] [reason: optional]

        """
        await ctx.defer()

        member_ids = self.get_member_ids(members)

        if len(member_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid member IDs provided.")
            await ctx.respond(embed=embed)

            return

        mute_role = await self.guild._fetch_role(self.cache["mutes"]["muteRole"])

        description = ""
        for member_id in member_ids:
            try:
                member: discord.Member = await self.guild.fetch_member(int(member_id))
            except Exception:
                description += f"The member with ID `{member_id}` was not found.\n"
                continue

            if mute_role not in member.roles:
                description += f"The member with ID `{member_id}` is not muted.\n"
                continue

            try:
                await member.remove_roles(mute_role, reason=reason)

                description += f"The member {member.mention} `{member.name}#{member.discriminator}` has been successfully unmuted."

                try:
                    self.cache[self._id]["unmute_queue"].pop(member_id)
                except KeyError:
                    pass
            except Exception as e:
                description += f"The member {member.mention} `{member.name}#{member.discriminator}` could not be unmuted.\n"
                print(e)
                continue

            if "unmutes" not in self.cache:
                self.cache["unmutes"] = {}
            self.cache["unmutes"].setdefault(str(member_id), []).append(
                {"responsible": ctx.author.id, "reason": reason, "time": datetime.now().timestamp()})

            self.bot.dispatch("member_unmute", ModContext(
                member=member, moderator=ctx.author, reason=reason, timestamp=datetime.now().timestamp()))

        await self.update_db(self._id)
        await self.update_db("unmutes")

        description = self.format_string(description)

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())

        new_line = "\n" #limitation of fstring
        embed.set_footer(text=f"Latest {description.count(new_line)} lines shown")

        await ctx.respond(embed=embed)

    async def _unmute(self, member, time):
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
            mute_role = await self.guild._fetch_role(self.cache["mutes"]["muteRole"])

            if mute_role not in member.roles:
                return

            await member.remove_roles(mute_role, reason="Automatic TC unmute")


            if "unmutes" not in self.cache:
                self.cache["unmutes"] = {}
            self.cache["unmutes"].setdefault(str(member_id), []).append(
                {"responsible": self.bot.user.id, "reason": f"Automated unmute", "time": datetime.now().timestamp()})

        except Exception as e:
            self.logger.error(f"{e}")

        self.cache[self._id]["unmute_queue"].pop(member_id)
        await self.update_db(self._id)
        await self.update_db("unmutes")

    def get_member_ids(self, ids):
        """
        Gets the IDs of members.

        """

        regex = r"\d+"

        return re.findall(regex, ids)

    def format_string(self, string) -> str:
        if len(string) < 4096:
            return string

        return string[-4096:][string.index('\n') + 2:]


        


def list_to_string(l):
    r = l[0]

    for i in l[1:-1]:
        r += ", " + i

    if len(l) > 1:
        r += " and " + l[-1]

    return r


def string_generator(length=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(length))

def setup(bot):
    bot.add_cog(Theorycrafting(bot))
    
def hash(s):
    return b64encode(bytes.fromhex(hashlib.sha224(s.encode()).hexdigest())).decode()[:16] #what the actual fuck
