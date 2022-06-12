import discord
from discord.ext import commands

from discord import Colour, Permissions, SlashCommandGroup

from core import checks
from core.base_cog import BaseCog
from core.checks import PermissionLevel

import re


class Configurator(BaseCog):
    _id = "config"

    default_cache = {
        "levelRoles": []
    }

    _cfg = SlashCommandGroup("config", "Contains all config commands.",
                             default_member_permissions=Permissions(manage_messages=True))

    _lvr = _cfg.create_subgroup(
        "levelrole", "Contains commands for managing level roles.")
    _mod = _cfg.create_subgroup(
        "modrole", "Contains commands for managing mod roles.")

    async def get_member_ids(self, ids):
        regex = r"\d{18}"

        return re.findall(regex, ids)

    @_cfg.command(name="reload", description="Reloads the config with data from the database.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _cfg_reload(self, ctx):
        """
        Reloads the config public variables.

        """

        await self.bot.config.load_cache_db(self.bot.db)

        embed = discord.Embed(title="Config", colour=Colour.blue())

        cache = self.bot.config.cache
        for name in cache:  # ignores sensitive info
            if name == "bot_token" or name == "pymongo_uri" or name == "_id":
                continue

            embed.add_field(name=name, value=cache[name], inline=False)

        await ctx.respond(embed=embed)

    @_lvr.command(name="add", description="Adds level roles.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _lvr_add(self, ctx, level_roles: discord.Option(str, "The roles you want to add.")):
        """
        Adds level roles for level related systems.

        """

        role_ids = await self.get_member_ids(level_roles)

        # stops if no valid ids were given
        if len(role_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid role IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        description = ""
        for role_id in role_ids:
            # checks if the level role already exists
            if int(role_id) in self.cache["levelRoles"]:
                description += f"The role <@&{role_id}> already exists in the database.\n"
            # checks if the role exists in the guild
            elif await self.guild._fetch_role(int(role_id)) == None:
                description += f"The role with ID `{role_id}` was not found in the guild."
            else:
                self.cache["levelRoles"].append(int(role_id))
                description += f"The role <@&{role_id}> was added into the database.\n"

        await self.update_db()

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

    @_lvr.command(name="remove", description="Removes level roles.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _lvr_remove(self, ctx, level_roles: discord.Option(str, "The roles you want to remove.")):
        """
        Removes level roles.

        """

        role_ids = await self.get_member_ids(level_roles)

        # stops if no valid ids were given
        if len(role_ids) == 0:
            embed = discord.Embed(
                title="Error", description="No valid role IDs provided.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        description = ""
        for role_id in role_ids:
            # checks if it exists in the database
            if int(role_id) not in self.cache["levelRoles"]:
                description += f"The role <@&{role_id}> does not exist in the database.\n"
            else:
                self.cache["levelRoles"].remove(int(role_id))
                description += f"The role <@&{role_id}> was removed from the database.\n"

        await self.update_db()

        embed = discord.Embed(
            title="Report", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

    @_lvr.command(name="list", description="Lists all the level roles.")
    @checks.has_permissions(PermissionLevel.TRIAL_MOD)
    async def _lvr_remove(self, ctx):
        """
        Lists all the level roles.

        """

        # stops if no level roles exist
        if len(self.cache["levelRoles"]) == 0:
            embed = discord.Embed(
                title="Error", description="No level roles in the database.", colour=Colour.red())
            await ctx.respond(embed=embed)

            return

        order = 1
        description = ""
        for role_id in self.cache["levelRoles"]:
            description += f"{order}: <@&{role_id}>\n"

            order = order + 1

        await self.update_db()

        embed = discord.Embed(
            title="Level roles", description=description, colour=Colour.blue())
        await ctx.respond(embed=embed)

    choices = [discord.OptionChoice("Theorycraft Admin", "tcAdmin"),
               discord.OptionChoice("Event Admin", "eventAdmin"),
               discord.OptionChoice("Mod", "mod"),
               discord.OptionChoice("Trial Mod", "trialMod"),
               discord.OptionChoice("Theorycraft Mod", "tcMod"),
               discord.OptionChoice("Event Mod", "eventMod")]

    @_mod.command(name="set", description="Sets mod roles.")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def _lvr_add(self, ctx, mod: discord.Option(str, "The kind of mod you want to set a role for.", choices=choices),
                       role: discord.Option(discord.Role, "The role you want to set.")):
        """
        Sets the various mod roles.

        """

        self.cache.update({mod: role.id})
        await self.update_db()

        embed = discord.Embed(
            title="Success", description=f"New {'' if mod == 'mod' else 'trial' if mod == 'trialMod' else 'theorycraft'} mod role set {role.mention}.", colour=Colour.green())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="ping", description="Returns bot latency.")
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def ping(self, ctx):
        await ctx.respond(f'Pong! {round (self.bot.latency * 1000)} ms')


def setup(bot):
    bot.add_cog(Configurator(bot))
