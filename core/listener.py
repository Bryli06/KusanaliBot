

from abc import ABC, abstractmethod 

class ModerationListener(ABC):

    @abstractmethod
    async def on_member_ban(self, ctx):
        pass

    @abstractmethod
    async def on_member_warn(self, ctx):
        pass

    @abstractmethod
    async def on_member_pardon(self, ctx):
        pass

    @abstractmethod
    async def on_member_unban(self, ctx):
        pass

    @abstractmethod
    async def on_member_kick(self, ctx):
        pass

    @abstractmethod
    async def on_member_mute(self, ctx):
        pass

    @abstractmethod
    async def on_member_unmute(self, ctx):
        pass

    async def trigger(self, event, ctx):
        if event == "ban":
            await self.on_member_ban(ctx)

        elif event == "unban":
            await self.on_member_unban(ctx)

        elif event == "warn":
            await self.on_member_warn(ctx)
        
        elif event == "pardon":
            await self.on_member_pardon(ctx)

        elif event == "kick":
            await self.on_member_kick(ctx)
        
        elif event == "mute":
            await self.on_member_mute(ctx)

        elif event == "unmute":
            await self.on_member_unmute(ctx)

        else:
            raise NotImplementedError(f"Invalid event: {event}")

class Context():
    def __init__(self, member, moderator, timestamp, reason = None, duration=None, id = None):
        self.member = member
        self.moderator = moderator
        self.timestamp = timestamp
        if duration:
            self.duration = duration
        if reason:
            self.reason = reason
        if id:
            self.id = id

