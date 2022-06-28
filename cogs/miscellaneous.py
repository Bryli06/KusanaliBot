import discord
from discord import ApplicationContext, Colour
import psutil
from discord.ext import commands

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


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
