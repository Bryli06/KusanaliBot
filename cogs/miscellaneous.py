import discord
from discord import ApplicationContext, Colour
import psutil
from discord.ext import commands

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel

class Miscellaneous(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="usage", description="Gets Usage")
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def usage(self, ctx: ApplicationContext):
        embed = discord.Embed(title="Stats", colour=Colour.green())

        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}", inline=False)
        embed.add_field(name="Memory Usage", value=f"{psutil.virtual_memory().used}/{psutil.virtual_memory().total} ({psutil.virtual_memory().percent}\%)", inline=False)
        embed.add_field(name="Disk Usage", value=f"{psutil.disk_usage('/').used}/{psutil.disk_usage('/').total} ({psutil.disk_usage('/').percent}\%)", inline=False)

        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Miscellaneous(bot))
