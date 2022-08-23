import discord
from discord.ext import commands

from discord import Colour

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel

class Chances(BaseCog):
    _id = "chances"

    def __deterministic(constellations=0, wishes=0):
        base = np.zeros((91,))
        base[0] = 0
        base[1:74] = P
        base[90] = 1
        for i in range(74, 90):
            base[i] = P + rampRate * (i-73)
        ones = np.ones((91,))
        temp = ones - base
        basePDF = np.zeros((91,))
        for i in range(91):
            basePDF[i] = np.prod(temp[0:i]) * base[i]
        doublePDF = np.zeros((181,))
        doublePDF[0:91] += basePDF
        for i in range(1, 90):
            doublePDF[i:i+91] += basePDF[i]*basePDF
        doublePDF *= 0.5
        fullPDF = doublePDF
        for i in range(constellations):
            fullPDF = np.convolve(fullPDF, doublePDF)
        return (fullPDF.cumsum()[wishes])

    @commands.slash_command(name="chances", description="Calculates your odds of getting a 5* and all constelations based on how many primogems/wishes/pity you have right now")
    async def chances (self, ctx: ApplicationContext, 
            primogems: discord.Option(int, "How many primogems you have"), 
            pity: discord.Option(int, "What pity are you at right now"),
            guarantee: discord.Option(bool, "Do you have guarantee or are you at 50/50")):

        wishes = primogems // 160 + pity + guarantee * 2
        
        embed = discord.Embed().from_dict({
            "title" : "Chances calculator",
            "description" : "Odds are calculated with the primogems you inputed, if you wish to calculate for a future banner make an estimate of primogems you'll have there",
            "color" : 4888823,
            "fields" : [
            {
                "name" : "C0",
                "value" : str(self.__deterministic(0, wishes))[:5],
                "inline" : True
            },
            {
                "name" : "C1",
                "value" : str(self.__deterministic(1, wishes))[:5],
                "inline" : True
            },
            {
                "name" : "C2",
                "value" : str(self.__deterministic(2, wishes))[:5],
                "inline" : True
            },
            {
                "name" : "C3",
                "value" : str(self.__deterministic(3, wishes))[:5],
                "inline" : True
            },
            {
                "name" : "C4",
                "value" : str(self.__deterministic(4, wishes))[:5],
                "inline" : True
            },
            {
                "name" : "C5",
                "value" : str(self.__deterministic(5, wishes))[:5],
                "inline" : True
            },
            {
                "name" : "C6",
                "value" : str(self.__deterministic(6, wishes))[:5],
                "inline" : True
            }]
        })

        await ctx.respond(embed=embed)

