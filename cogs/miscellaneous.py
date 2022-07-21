import discord
from discord import ApplicationContext, Colour
import psutil
from discord.ext import commands

from contextlib import redirect_stdout
import requests
import re

from io import BytesIO, StringIO

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel

class Miscellaneous(BaseCog):
    _id="miscellaneous"
    
    default_cache={}

    @commands.slash_command(name="usage", description="Gets Usage")
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def usage(self, ctx: ApplicationContext):
        embed = discord.Embed(title="Stats", colour=Colour.green())

        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}", inline=False)
        embed.add_field(name="Memory Usage", value=f"{psutil.virtual_memory().used}/{psutil.virtual_memory().total} ({psutil.virtual_memory().percent}\%)", inline=False)
        embed.add_field(name="Disk Usage", value=f"{psutil.disk_usage('/').used}/{psutil.disk_usage('/').total} ({psutil.disk_usage('/').percent}\%)", inline=False)

        await ctx.respond(embed=embed)


    @commands.slash_command(name="run", description="Run a command")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def run(self, ctx: ApplicationContext, url: discord.Option(str, "Pastebin of the code to execute")):
        
        regex = r"(?<=com/)"
        url = re.sub(regex, "raw/", url)

        sio = StringIO()
        with redirect_stdout(sio):
            exec(requests.get(url).text)
    
        bio = BytesIO(sio.getvalue().encode('utf8'))

        await ctx.respond(file=discord.File(fp=bio, filename="output.txt"))



def setup(bot):
    bot.add_cog(Miscellaneous(bot))
