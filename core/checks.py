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
    TC_MOD = 1
    TRIAL_MOD = 2
    MOD = 3
    ADMINISTRATOR = 4
    OWNER = 5
    

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

    # Check for server/bot ownership
    if await ctx.bot.is_owner(ctx.author) or ctx.author.id == ctx.bot.user.id or ctx.author.id == ctx.guild.owner_id or str(ctx.author.id) in ctx.bot.config["owners"]:
        return True

    # Check for administrator
    if permission_level is not PermissionLevel.OWNER and ctx.channel.permissions_for(ctx.author).administrator:
        return True

    # Check for mod
    if permission_level is not PermissionLevel.ADMINISTRATOR and ctx.author.get_role(ctx.bot.config["mod"]) != None:
        return True

    # Check for trial mod
    if permission_level is not PermissionLevel.MOD and ctx.author.get_role(ctx.bot.config["trialMod"]) != None:
        return True

    # Check for theorycraft mod
    if permission_level is not PermissionLevel.TRIAL_MOD and ctx.author.get_role(ctx.bot.config["tcMod"]) != None:
        return True

    # Check if it's a regular user
    if permission_level is PermissionLevel.REGULAR:
        return True

    if permission_level is None:
        logger.error(f"Invalid permission level: {permission_level.__str__}")

    raise commands.CheckFailure("You do not have the required permissions.")
