from distutils.filelist import findall
from random import choices
from tabnanny import check
from typing import Iterable
import discord
from discord.ext import commands
from discord.ui import Select, Button, View

from discord import ApplicationContext, ChannelType, Interaction, OptionChoice, SlashCommandGroup, TextChannel, message_command

from core import checks
from core.checks import PermissionLevel

from core.logger import get_logger

import re

from json import dumps

logger = get_logger(__name__)


class Configurator(commands.Cog):
    _id = "config"

    default_cache = {
        "levelRoles": []
    }

    _cfg = SlashCommandGroup("config", "Contains all config commands.")
    _lvr = _cfg.create_subgroup(
        "levelrole", "Contains commands for managing level roles.")

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

    async def get_member_ids(self, ids):
        regex = r"(?<=<@&)\d*(?=>)"

        return re.findall(regex, ids)

    @_cfg.command(name="reload", description="Reloads the config with data from the database.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _cfg_reload(self, ctx):
        await self.bot.config.load_cache_db(self.bot.db)

        embed = discord.Embed(title="Config")

        cache = self.bot.config.cache
        for name in cache:
            if name == "bot_token" or name == "_id":
                continue

            embed.add_field(name=name, value=cache[name], inline=False)

        await ctx.respond(embed=embed)

    @_lvr.command(name="add", description="Adds level roles.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _lvr_add(self, ctx, level_roles: discord.Option(str, "The roles you want to add.")):
        role_ids = await self.get_member_ids(level_roles)

        if len(role_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid role IDs provided.")
            await ctx.respond(embed=embed)

            return

        guild: discord.Guild = self.bot.get_guild(self.bot.config["guild_id"])

        description = ""
        for role_id in role_ids:
            if int(role_id) in self.cache["levelRoles"]:
                description += f"The role <@&{role_id}> already exists in the database.\n"
            elif guild.get_role(int(role_id)) == None:
                description += "The role was not found in the guild."
            else:
                self.cache["levelRoles"].append(int(role_id))
                description += f"The role <@&{role_id}> was added into the database.\n"

        await self.update_db()

        embed = discord.Embed(
            title="Report", description=description)
        await ctx.respond(embed=embed)

    @_lvr.command(name="remove", description="Removes level roles.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _lvr_remove(self, ctx, level_roles: discord.Option(str, "The roles you want to remove.")):
        role_ids = await self.get_member_ids(level_roles)

        if len(role_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid role IDs provided.")
            await ctx.respond(embed=embed)

            return

        description = ""
        for role_id in role_ids:
            if int(role_id) not in self.cache["levelRoles"]:
                description += f"The role <@&{role_id}> does not exist in the database.\n"
            else:
                self.cache["levelRoles"].remove(int(role_id))
                description += f"The role <@&{role_id}> was removed from the database.\n"

        await self.update_db()

        embed = discord.Embed(
            title="Report", description=description)
        await ctx.respond(embed=embed)

    @_lvr.command(name="list", description="Lists all the level roles.")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _lvr_remove(self, ctx):
        if len(self.cache["levelRoles"]) == 0:
            embed = discord.Embed(
                title="Error", description="No level roles in the database.")
            await ctx.respond(embed=embed)

            return

        order = 1
        description = ""
        for role_id in self.cache["levelRoles"]:
            description += f"{order}: <@&{role_id}>\n"

            order = order + 1

        await self.update_db()

        embed = discord.Embed(
            title="Level roles", description=description)
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Configurator(bot))
