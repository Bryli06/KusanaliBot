import discord
from discord.ext import commands
from discord import SlashCommandGroup, ApplicationContext, SlashCommand, option
from discord.commands import Option
from datetime import datetime

from core.time import UserFriendlyTime
from core import checks
from core.logger import get_logger
from core import settings

logger = get_logger(__name__)
guild_id = settings.guild_id


class Moderation(commands.Cog):
    _id = "moderation"

    default_cache = {
        "ban":{
                
        },

        "kick": {
            
        },

        "warn": {

        },

        "note": {

        },

        "tempban": { #stores members who need to be tempbanned and what time to unban

        }, 
    }
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db[self._id]
        self.cache = {}

        self.bot.loop.create_task(self.load_cache())

    async def update_db(self):  # updates database with cache
        await self.db.find_one_and_update(
            {"_id": self._id},
            {"$set": self.cache},
            upsert=True,
        )

    async def load_cache(self):
        db = await self.db.find_one({"_id": self._id})
        if db is None:
            db = self.default_cache

        self.cache = db

        for key, value in self.cache["tempban"]:
            await self.unban(key, value)

    @commands.slash_command(name = "ban", description = "Bans a member")
    @discord.default_permissions(ban_members = True)
    @option("member", commands.Greedy[discord.Member], description="The members you want to ban.", required = True)
    @option("duration", UserFriendlyTime, description="How long to ban the member for. Leave blank to permenantly ban.", default = None, required = False)
    @option("reason", str, description="Reason to ban", default = "", required = False)
    async def ban(self, ctx: ApplicationContext, member: commands.Greedy[discord.Member], duration: UserFriendlyTime, reason: str):
        """Bans a member via /ban [members] [duration: Optional] [reason: Optional]"""
        member_list = ""
        for members in member:
            member_list += "\n" + str(members.id)
            await ctx.guild.ban(members,reason=reason)
            if duration:
                self.cache["tempban"][str(members.id)] = duration.dt
                await self.unban(members.id, duration.dt)

            self.cache["ban"][str(members.id)] = {"reason": reason, "responsible": ctx.author.id} 
        await self.update_db()
        embed = discord.Embed(title="Success", description = f"Successfully banned: {member_list}")
        await ctx.respond(embed=embed)

    async def unban(self, member, time):
        now = datetime.utcnow()
        closetime = (time.dt - now).total_seconds() if time else 0 
        
        if closetime > 0:
            self.bot.loop.call_later(closetime, self._unban_after, member)
        else: 
            await self._unban(member)

    def _unban_after(self, member): #bruh async stuff
        return self.bot.loop.create_task(self._unban(member))

    async def _unban(self, member):
        await self.bot.get_guild(guild_id).unban(member)


def setup(bot):
    bot.add_cog(Moderation(bot))
