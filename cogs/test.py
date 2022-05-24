import discord
from discord.ext import commands
from discord.commands import slash_command, Option

from core.logger import get_logger

logger = get_logger(__name__)

class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == 906318377432281088:
            await message.channel.send("working!")

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(self.get_commands())

    @slash_command(name="test", guild_ids=[977013237889523712])
    async def test(self, ctx):
        await ctx.send("test")


def setup(bot):
    bot.add_cog(Test(bot))
