from typing import Callable, TypeVar
import discord
from discord.ext import commands

from enum import Enum
from core.logger import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


class PermissionLevel(Enum):
    def __str__(self):
        return self.name

    # enjoy some wet comments

    # regular users
    REGULAR = 0

    # all staff
    STAFF = 1
    
    # section mods
    TC_MOD = 2
    EVENT_MOD = 3
    
    # trial mods
    TRIAL_MOD = 4

    # regular mods
    MOD = 5

    # section admins
    EVENT_ADMIN = 6
    TC_ADMIN = 7

    # admins
    ADMINISTRATOR = 8

    # owner
    OWNER = 9
    

def only_modmail_thread(modmail_channel_id) -> Callable[[T], T]:
    """
    A decorator that checks if the channel is a modmail thread.

    """

    async def predicate(ctx) -> bool:
        if type(ctx.channel) == discord.threads.Thread and ctx.channel.parent_id == modmail_channel_id:
            return True

        embed = discord.Embed(
            title="Error", description="You can't use this command here.")

        await ctx.respond(embed=embed, ephemeral=True)

        raise commands.CheckFailure("You can't use this command here.")

    return commands.check(predicate)


def has_permissions(permission_level: PermissionLevel = PermissionLevel.REGULAR) -> Callable[[T], T]:
    """
    A decorator that checks if the author has the required permissions.

    """

    async def predicate(ctx) -> bool:
        return await check_permissions(ctx, permission_level)

    return commands.check(predicate)


async def check_permissions(ctx: commands.Context, permission_level) -> bool:
    """
    Checks if a user has the permissions required.

    """

    # check for server/bot ownership
    if await ctx.bot.is_owner(ctx.author) or ctx.author.id == ctx.bot.user.id or ctx.author.id == ctx.guild.owner_id or str(ctx.author.id) in ctx.bot.config["owners"]:
        return True

    # check for admin
    if permission_level is not PermissionLevel.OWNER:
        if ctx.channel.permissions_for(ctx.author).administrator:
            return True

    # check for section admin
    if permission_level is not PermissionLevel.ADMINISTRATOR:
        if  ctx.author.get_role(ctx.bot.config["tcAdmin"]) != None:
            return True

        if  ctx.author.get_role(ctx.bot.config["eventAdmin"]) != None:
            return True

    # check for mod
    if permission_level is not PermissionLevel.TC_ADMIN and permission_level is not PermissionLevel.EVENT_ADMIN:
        if ctx.author.get_role(ctx.bot.config["mod"]) != None:
            return True

    # check for trial mod
    if permission_level is not PermissionLevel.MOD:
        if ctx.author.get_role(ctx.bot.config["trialMod"]) != None:
            return True

    # check for section mod
    if permission_level is not PermissionLevel.TRIAL_MOD:
        if  ctx.author.get_role(ctx.bot.config["tcMod"]) != None:
            return True

        if  ctx.author.get_role(ctx.bot.config["eventMod"]) != None:
            return True

    # check for staff
    if permission_level is not PermissionLevel.TC_MOD and permission_level is not PermissionLevel.EVENT_MOD:
        if ctx.channel.permissions_for(ctx.author).manage_messages:
            return True

    # check for regular user
    if permission_level is PermissionLevel.REGULAR:
        return True

    if permission_level is None:
        logger.error(f"Invalid permission level: {permission_level.__str__}")

    raise commands.CheckFailure("You do not have the required permissions.")
