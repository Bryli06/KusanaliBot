import discord
import numpy as np
import math
from discord.ext import commands


from discord import Colour, ApplicationContext

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel

class Chances(BaseCog):
    _id = "chances"

    default_cache = {}
    
    @commands.slash_command(name="chances", description="Calculates your odds of getting a 5* and all constelations")
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def chances (self, ctx: ApplicationContext, 
            wishes: discord.Option(int, "How many fates you have"), 
            pity: discord.Option(int, "What pity are you at right now"),
            guarantee: discord.Option(bool, "Do you have guarantee or are you at 50/50")):
        
        guarantee = 1 if guarantee else 0

        P = 0.006
        ramp_rate = 0.06
        
        cum_prob = np.zeros((91,))
        cum_prob[0] = 0
        cum_prob[1:74] = P
        cum_prob[90] = 1
        for i in range(74, 90):
            cum_prob[i] = P + ramp_rate * (i-73)
        ones = np.ones((91,))
        complement = ones - cum_prob

        base_gf_coefficents = np.zeros((91, ))
        for i in range(91):
            base_gf_coefficents[i] = np.prod(complement[0:i]) * cum_prob[i]

        gf_coefficents = np.zeros((14, 1 + 90*14))

        pity_sum = np.cumsum(base_gf_coefficents)[pity]

        gf_coefficents[0][pity+1:91] = base_gf_coefficents[pity+1:] / (1-pity_sum)

        for i in range(1, 14):
            for j in range(1, 90*i+1):
                gf_coefficents[i][j: j+91] += gf_coefficents[i-1][j] * base_gf_coefficents[0:91]


        five_star_prob = gf_coefficents.cumsum(axis=1)[:, wishes+pity]
        
        embed = discord.Embed().from_dict({
            "title" : "Chances calculator",
            "description" : "Odds are calculated with the rolls you inputed, if you wish to calculate for a future banner make an estimate of how many pulls you'll have there",
            "color" : 4888823,
        })

        for i in range(7):
            embed.add_field(name=f"C{i}", value=f"{np.format_float_positional((100 * np.dot([math.comb(i+1-guarantee, j)/(2 ** (i+1-guarantee)) for j in range(i+2-guarantee) ], five_star_prob[i:2*i+2-guarantee])), precision=4, unique=False, fractional=False, trim='k')}%")

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Chances(bot))
