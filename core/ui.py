import discord
from discord.ui import Button, View, Select, Modal, InputText
from discord import ApplicationContext, Colour, SlashCommandGroup, Interaction, TextChannel, OptionChoice


class captcha_modal(discord.ui.Modal):
    def __init__(self, cog, answer, prev_view, prev_interaction, view): 
        self.cog = cog
        self.answer = answer #correct answer to captcha
        self.prev_view = prev_view #view object that opens modal
        self.prev_interaction = prev_interaction
        self.view = view #view to show in the success embed


        super().__init__(InputText(label="ANSWER"), title="Verify Yourself")

    async def callback(self, interaction: discord.Interaction):
        await self.cog.captcha_log(interaction.user, self.children[0].value, self.answer)

        if self.answer == self.children[0].value:
            self.prev_view.disable_all_items()
            self.prev_view.stop()

            await self.prev_interaction.edit_original_message(view=self.prev_view)

            embed = discord.Embed(title="Success", description="Please now make your vote")
            
            await interaction.response.send_message(embed=embed, view=self.view, ephemeral=True)

            return

        embed = discord.Embed(title="Error", description="Could not verify, please try again")

        await interaction.response.send_message(embed=embed, ephemeral=True)




