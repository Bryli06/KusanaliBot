import discord
from discord.ui import Button, View, Select
from discord import ApplicationContext, Colour, SlashCommandGroup, Interaction, TextChannel, OptionChoice
from discord.ext import commands


from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel

class Theorycrafting(BaseCog):
    _id="theorycrafting"
    
    default_cache={
        "active": [],
        "archive": [],
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

    _lgr = SlashCommandGroup("logger", "Commands regarding the logger", )
    _tc = SlashCommandGroup("theorycrafting", "Commands specific for theorycrafting")


    async def after_load(self):
        for message_id in self.cache[self._id]["active"]:
            await self.start_vote(message_id)
        

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

    @_vote.command(name="create", description="create an anonymous poll with options yes, no, abstain")
    @checks.has_permissions(PermissionLevel.TC_ADMIN)
    async def vote_create(self, ctx: ApplicationContext, title: discord.Option(str, "Title of the poll"), description: discord.Option(str, "Description of the poll")):
        
        await ctx.defer(ephemeral=True)

        embed = discord.Embed(title=title, description=description, color=Colour.blue())

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
                    "yes": [],
                    "no": [],
                    "abstain": [],
                    "title": title,
                    "channel": ctx.channel.id, 
                }

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


    @_vote.command(name="end", description="ends an existing vote")
    @checks.has_permissions(PermissionLevel.TC_ADMIN)
    async def vote_end(self, ctx: ApplicationContext):

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

            poll = self.cache[message_id]

            embed = message.embeds[0]
            embed.description = f"{embed.description}\n\n__Results:__\nYes: {len(poll['yes'])}\nNo: {len(poll['no'])}\nAbstain: {len(poll['abstain'])}"
            embed.colour = Colour.red()

            await message.edit(embed=embed, view=None)

            embed=discord.Embed(title="Report", description="Successfully ended vote and results shown.")

            await interaction.response.send_message(embed=embed)

        select.callback = _select_callback

        view = View(select, timeout=60)
        await ctx.respond(view=view, ephemeral=True)



    async def add_buttons(self, message: discord.Message):
        
        async def _yes_callback(interaction: Interaction):
            poll = self.cache[message.id]

            user_id = interaction.user.id

            if user_id in poll["yes"]:
                embed = discord.Embed(
                        title="Warning", description="You have already voted for Yes",
                        colour=Colour.red())

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            if user_id in poll["no"]:
                poll["no"].remove(user_id)
                poll["yes"].append(user_id)

                await self.update_db(message.id)

                embed = discord.Embed(title="Report", description="Switched vote from No to Yes.", colour=Colour.green())

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return
                

            if user_id in poll["abstain"]:
                poll["abstain"].remove(user_id)
                poll["yes"].append(user_id)

                await self.update_db(message.id)

                embed = discord.Embed(title="Report", description="Switched vote from Abstain to Yes.", colour=Colour.green())

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            poll["yes"].append(user_id)
            
            await self.update_db(message.id)

            embed = message.embeds[0]
            embed.title = f"{poll['title']} ({len(poll['yes']) + len(poll['no']) + len(poll['abstain'])} voted)"

            await message.edit(embed=embed)
                
            embed = discord.Embed(title="Report", description="Successfully voted for Yes.", colour=Colour.green())

            await interaction.response.send_message(embed=embed, ephemeral=True)
            

        async def _no_callback(interaction: Interaction):
            poll = self.cache[message.id]

            user_id = interaction.user.id

            if user_id in poll["no"]:
                embed = discord.Embed(
                        title="Warning", description="You have already voted for No",
                        colour=Colour.red())

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            if user_id in poll["yes"]:
                poll["yes"].remove(user_id)
                poll["no"].append(user_id)

                await self.update_db(message.id)

                embed = discord.Embed(title="Report", description="Switched vote from Yes to No.", colour=Colour.green())

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return
                

            if user_id in poll["abstain"]:
                poll["abstain"].remove(user_id)
                poll["no"].append(user_id)

                await self.update_db(message.id)

                embed = discord.Embed(title="Report", description="Switched vote from Abstain to No.", colour=Colour.green())

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            poll["no"].append(user_id)
            
            await self.update_db(message.id)

            embed = message.embeds[0]
            embed.title = f"{poll['title']} ({len(poll['yes']) + len(poll['no']) + len(poll['abstain'])} voted)"

            await message.edit(embed=embed)
            
            embed = discord.Embed(title="Report", description="Successfully voted for No.", colour=Colour.green())

            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        async def _abstain_callback(interaction: Interaction):
            poll = self.cache[message.id]

            user_id = interaction.user.id

            if user_id in poll["abstain"]:
                embed = discord.Embed(
                        title="Warning", description="You have already voted for Abstain",
                        colour=Colour.red())

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            if user_id in poll["yes"]:
                poll["yes"].remove(user_id)
                poll["abstain"].append(user_id)

                await self.update_db(message.id)

                embed = discord.Embed(title="Report", description="Switched vote from Yes to Abstain.", colour=Colour.green())

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return
                

            if user_id in poll["no"]:
                poll["no"].remove(user_id)
                poll["abstain"].append(user_id)

                await self.update_db(message.id)

                embed = discord.Embed(title="Report", description="Switched vote from No to Abstain.", colour=Colour.green())

                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

            poll["abstain"].append(user_id)
            
            await self.update_db(message.id)

            embed = message.embeds[0]
            embed.title = f"{poll['title']} ({len(poll['yes']) + len(poll['no']) + len(poll['abstain'])} voted)"

            await message.edit(embed=embed)
            
            embed = discord.Embed(title="Report", description="Successfully voted for Abstain.", colour=Colour.green())

            await interaction.response.send_message(embed=embed, ephemeral=True)

        yes = Button(label="Yes", style=discord.ButtonStyle.blurple)
        yes.callback = _yes_callback

        no = Button(label="No", style=discord.ButtonStyle.blurple)
        no.callback = _no_callback

        abstain = Button(label="Abstain", style=discord.ButtonStyle.blurple)
        abstain.callback = _abstain_callback

        view = View(yes, no, abstain, timeout=None)

        await message.edit(view=view)
                
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



def setup(bot):
    bot.add_cog(Theorycrafting(bot))
