import discord
from discord.ui import Button, View, Select, Modal, InputText
from discord import ApplicationContext, Colour, SlashCommandGroup, Interaction, TextChannel, OptionChoice, Permissions
from discord.ext import commands

import cogs.theorycrafting as tc
from core.checks import PermissionLevel
from core import checks
class Amongus(commands.Cog):

    _sus = SlashCommandGroup("amongus", "sussy baka")

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        
        self.bot.loop.create_task(self.load_cache())
        
    async def load_cache(self):
        await self.bot.increment_tasks()

    async def get_theorycrafting(self):
        cogs = self.bot.get_cog("Theorycrafting")
        self.theorycrafting = cogs
        self.cache = cogs.cache

    async def after_load(self):
        return
    

    @_sus.command(name="sus", description="When imposter is sus", default_member_permissions=Permissions(administrator=True))
    @checks.has_permissions(PermissionLevel.TC_ADMIN)
    async def vote_results(self, ctx: ApplicationContext):
        await self.get_theorycrafting()

        if not self.cache[self.theorycrafting._id]["active"]:
            embed = discord.Embed(title="Error", description="No active votes.", colour=Colour.red())

            await ctx.respond(embed=embed, ephemeral=True)
            return

        options = []
        for i, vote in enumerate(self.cache[self.theorycrafting._id]["active"]):
            options.append(discord.SelectOption(
                label=self.cache[vote]["title"],
                value=str(i),
                ))
        select = Select(
            placeholder="Select which vote to alter",
            options=options,
            )
        
        async def _select_callback(interaction: discord.Interaction):
            await interaction.response.send_modal(my_modal(self, self.cache[self.theorycrafting._id]["active"][int(select.values[0])]))

        select.callback = _select_callback

        view = View(select, timeout=60)
        await ctx.respond(view=view, ephemeral=True)
    

            


class my_modal(discord.ui.Modal):
    def __init__(self, cog, message_id): 
        self.cog = cog

        self.cache = cog.cache
        
        self.message_id = message_id

        labels = []


        for k, v in self.cache[message_id]['options'].items():
            labels.append(InputText(label=f"Number of votes to change {k} to: ({v}/{len(self.cache[message_id]['voters'])})"))

        super().__init__(*labels, title="Edit Values")


    async def callback(self, interaction: discord.Interaction):
        i = 0
        for k in self.cache[self.message_id]['options']:
            self.cache[self.message_id]['options'][k] = int(self.children[i].value)
            i += 1

        await self.cog.theorycrafting.update_db(self.message_id) 
            
        embed = discord.Embed(title="Success", description=f"__New Results:__\n{self.cog.theorycrafting.get_results(self.message_id)}")
            
        await interaction.response.send_message(embed=embed, ephemeral=True)



def setup(bot):
    bot.add_cog(Amongus(bot))
