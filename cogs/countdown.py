import asyncio

import discord
from discord.ext import commands
from discord import ApplicationContext, Colour, Permissions, SlashCommandGroup

import io
from datetime import datetime, timezone
from dateutil import relativedelta

from core import checks
from core.time import InvalidTime, TimeConverter
from core.checks import PermissionLevel
from core.base_cog import BaseCog

from PIL import Image, ImageFont, ImageDraw


class Countdown(BaseCog):
    _id = "countdown"

    kusanali_drop = 1665903600 #november 16th 2022

    default_cache = { }

    _cd = SlashCommandGroup("countdown", "Manages countdown channels.",
                            default_member_permissions=Permissions(manage_messages=True))

    async def load_cache(self): #each countdown gets its own document
        cursor = self.db.find({ })
        docs = await cursor.to_list(length=10) #how many documents to buffer shouldn't be too high
        while docs:
            for document in docs:
                _id = document.pop("_id")
                self.cache[_id] = document

            docs = await cursor.to_list(length=10)
        
        self.guild: discord.Guild = await self.bot.fetch_guild(self.bot.config["guild_id"])
        
        await self.bot.increment_tasks()

            


    async def update_db(self, _id): #we need a different insert command that allows us to insert into seperate documents
        if _id not in self.cache:
            await self.db.delete_one({"_id": _id})
            return

        await self.db.find_one_and_update(
            {"_id": _id},
            {"$set": self.cache[_id]},
            upsert=True,
        )

    async def after_load(self):
        await self.start_countdowns()

    async def start_countdowns(self):
        for k, v in list(self.cache.items()):
            self.bot.loop.create_task(self.start_countdown(k))

    async def start_countdown(self, channel_id):
        channel = await self.guild.fetch_channel(int(channel_id))

        if not channel:
            self.cache.pop(str(channel_id))
            await self.update_db(str(channel_id))
            
            return

        while True:
            if not await self.update(self.cache[str(channel_id)]["name"], self.cache[str(channel_id)]["date"].replace(tzinfo=timezone.utc), channel):
                return

    async def update(self, name, date, channel):
        diff = relativedelta.relativedelta(date,
                                            datetime.now(timezone.utc))

        if date < datetime.now(timezone.utc):
            await channel.edit(name=name)
            self.cache.pop(str(channel.id))

            await self.update_db(str(channel.id))

            return False

        years = diff.years
        months = diff.months
        days = diff.days
        hours = diff.hours
        minutes = diff.minutes
        seconds = diff.seconds

        if years > 1:
            if months >= 6:
                years += 1

            await channel.edit(name=f"{name}: {years} years")
            await asyncio.sleep(31556952)

        elif months > 1:
            if days > 15:
                months += 1

            await channel.edit(name=f"{name}: {months} months")
            await asyncio.sleep(2629800)

        elif days > 1:
            if hours >= 12:
                days += 1

            await channel.edit(name=f"{name}: {days} days")
            await asyncio.sleep(86400)

        elif hours > 1:
            if minutes >= 30:
                hours += 1

            await channel.edit(name=f"{name}: {hours} hours")
            await asyncio.sleep(3600)

        elif minutes > 1:
            if seconds >= 30:
                minutes += 1
            await channel.edit(name=f"{name}: {minutes} minutes")
            await asyncio.sleep(300)

        elif seconds:
            await channel.edit(name=f"{name}: A few seconds")
            await asyncio.sleep(seconds)

        else:
            await channel.edit(name=name)
            return False

        return True

    @_cd.command(name="create", description="Create a countdown using a date.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def create(self, ctx: ApplicationContext, name: discord.Option(str, description="Message you would like to count down"),
                     end: discord.Option(str, "When the countdown ends")):
        """
        Creates a new countdown in the form of a voice channel.

        """
        date = None
        try:
            date = TimeConverter(end).final
        except InvalidTime as e:
            embed = discord.Embed(
                    title="Error", description=e, colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        vc = None

        try:
            vc = await self.guild.create_voice_channel(name=name, category=ctx.channel.category)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Error", description="Bot does not have permissions.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        self.cache[str(vc.id)] = {"name": name, "date": date}
        await self.update_db(str(vc.id))

        self.bot.loop.create_task(self.start_countdown(str(vc.id)))

        embed = discord.Embed(
            title="Success", description="Countdown created.", colour=Colour.green())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="cd", description="Gets duration until Kusanali Drop.")
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def cd(self, ctx: ApplicationContext):
        """
        Gets the countdown until Kusanali drop and sends it as an image.

        """
        await ctx.defer()

        diff = round(Countdown.kusanali_drop 
                        - datetime.now().timestamp())

        m, r = divmod(diff, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        font = ImageFont.truetype("./fonts/blue-yellow.ttf", 250)
        cd_image = Image.open("./assets/countdown_template.jpg")

        draw = ImageDraw.Draw(cd_image)

        # coordinates found via pixspy.com
        width, height = get_text_dimensions(f"{d}", font)
        draw.text((232-width/2, 538-height/2), f"{d}", font=font)

        width, height = get_text_dimensions(f"{h}", font)
        draw.text((618-width/2, 538-height/2), f"{h}", font=font)

        width, height = get_text_dimensions(f"{m}", font)
        draw.text((1003-width/2, 538-height/2), f"{m}", font=font)

        temp = io.BytesIO()
        cd_image.save(temp, format="png")
        temp.seek(0)

        await ctx.respond(file=discord.File(fp=temp, filename="cd.png"))


def get_text_dimensions(text_string, font):
    ascent, descent = font.getmetrics()

    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return (text_width, text_height)

def setup(bot):
    bot.add_cog(Countdown(bot))
