from distutils.filelist import findall
from random import choices
from tabnanny import check
from typing import Iterable
import discord
from discord.ext import commands
from discord.ui import Select, Button, View

from discord import ApplicationContext, ChannelType, Interaction, OptionChoice, SlashCommandGroup, TextChannel, message_command

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel

import re


class Configurator(BaseCog):
    _id = "config"

    default_cache = {
        "levelRoles": []
    }

    _cfg = SlashCommandGroup("config", "Contains all config commands.")
    _lvr = _cfg.create_subgroup(
        "levelrole", "Contains commands for managing level roles.")
    _mod = _cfg.create_subgroup(
        "modrole", "Contains commands for managing mod roles.")

    def __init__(self, bot) -> None:
        super().__init__(bot)

    async def get_member_ids(self, ids):
        regex = r"\d{18}"

        return re.findall(regex, ids)

    @_cfg.command(name="reload", description="Reloads the config with data from the database.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _cfg_reload(self, ctx):
        await self.bot.config.load_cache_db(self.bot.db)

        embed = discord.Embed(title="Config")

        cache = self.bot.config.cache
        for name in cache:
            if name == "bot_token" or name == "pymongo_uri" or name == "_id":
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

        description = ""
        for role_id in role_ids:
            if int(role_id) in self.cache["levelRoles"]:
                description += f"The role <@&{role_id}> already exists in the database.\n"
            elif self.guild.get_role(int(role_id)) == None:
                description += f"The role with ID `{role_id}` was not found in the guild."
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

    @_mod.command(name="set", description="Sets mod roles.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _lvr_add(self, ctx, mod: discord.Option(str, "The kind of mod you want to set a role for.",
                       choices=[discord.OptionChoice("Mod", "mod"), discord.OptionChoice("Trial Mod", "trialMod"), discord.OptionChoice("Theorycraft Mod", "tcMod")]),
                       role: discord.Option(discord.Role, "The role you want to set.")):
        self.cache.update({mod: role.id})
        await self.update_db()

        embed = discord.Embed(
            title="Success", description=f"New {'' if mod == 'mod' else 'trial' if mod == 'trialMod' else 'theorycraft'} mod role set {role.mention}.")
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Configurator(bot))
