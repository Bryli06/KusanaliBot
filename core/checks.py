import discord
from discord.ext import commands

from enum import Enum
from logger import get_logger


logger = get_logger(__name__)


class PermissionLevel(Enum):
    def __str__(self):
        return self.name

    REGULAR = 0
    ADMINISTRATOR = 1
    OWNER = 2


def has_permissions_predicate(permission_level: PermissionLevel = PermissionLevel.REGULAR,):
    async def predicate(ctx):
        return await check_permissions(ctx, permission_level)

    predicate.permission_level = permission_level

    return predicate


def has_permissions(permission_level: PermissionLevel = PermissionLevel.REGULAR):
    """
    A decorator that checks if the author has the required permissions.

    """

    return commands.check(has_permissions_predicate(permission_level))


async def check_permissions(ctx, permission_level) -> bool:
    """
    Checks if a user has the permissions required.

    """

    if await ctx.bot.is_owner(ctx.author) or ctx.author.id == ctx.bot.user.id or ctx.author.id == ctx.guild.owner_id or ctx.author.id in ctx.bot.settings.cache["owners"]:
        return True

    if permission_level is not PermissionLevel.OWNER and ctx.channel.permissions_for(ctx.author).administrator:
        return True

    if permission_level is PermissionLevel.REGULAR:
        return True

    if permission_level not in PermissionLevel:
        logger.error(f"Invalid permission level: {permission_level.__str__}")

    return False
