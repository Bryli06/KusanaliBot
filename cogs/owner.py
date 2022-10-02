import discord
from discord.ext import commands
from discord import ApplicationContext

from core import checks
from core.checks import PermissionLevel

class Owner(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.bot.loop.create_task(self.done())
    
    async def done(self):
        await self.bot.increment_tasks()

    async def after_load(self):
        pass


    @commands.slash_command(name="reload", description="Reload cog by name",
            default_member_permissions=discord.Permissions(administrator=True))
    @checks.has_permissions(PermissionLevel.OWNER)
    async def reload(self, ctx: ApplicationContext,
            cog: discord.Option(str, "The name of the cog to reload")):
        try:
            self.bot.add_cog(self.bot.remove_cog(cog))
        except Exception as e:
            embed = discord.Embed(title=f"Error reloading cog {cog}", description=f"{type(e).__name__} - {e}")
            await ctx.respond(embed=embed)

        else:
            embed = discord.Embed(title=f"Success", description=f"Reloaded cog {cog} successfully")
            await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Owner(bot))
