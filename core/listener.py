



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

