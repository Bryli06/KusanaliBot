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

    REGULAR = 0
    ADMINISTRATOR = 1
    OWNER = 2


def has_permissions(permission_level: PermissionLevel = PermissionLevel.REGULAR) -> Callable[[T], T]:
    """
    A decorator that checks if the author has the required permissions.

    """

    async def predicate(ctx) -> bool:
        return await check_permissions(ctx, permission_level)

    return commands.check(predicate)


async def check_permissions(ctx: discord.ApplicationContext, permission_level) -> bool:
    """
    Checks if a user has the permissions required.

    """

    # Check for server/bot ownership
    if await ctx.bot.is_owner(ctx.author) or ctx.author.id == ctx.bot.user.id or ctx.author.id == ctx.guild.owner_id or str(ctx.author.id) in ctx.bot.settings.cache["owners"]:
        return True

    # Check for administrator
    if permission_level is not PermissionLevel.OWNER and ctx.channel.permissions_for(ctx.author).administrator:
        return True

    # Check if it's a regular user
    if permission_level is PermissionLevel.REGULAR:
        return True

    commands.is_owner()

    if permission_level is None:
        logger.error(f"Invalid permission level: {permission_level.__str__}")

    embed = discord.Embed(
        title="Error", description="You do not have the required permissions.")

    await ctx.respond(embed=embed, ephemeral=True)

    raise commands.CheckFailure("You do not have the required permissions.")
