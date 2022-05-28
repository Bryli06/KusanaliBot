from copy import deepcopy
import os
from dotenv import load_dotenv

from pydoc import locate

load_dotenv()


class Config:
    _id = "config"

    bot_config = {
        "activity_type": int,
        "bot_token": str,
        "guild_id":  int,
        "log":  str,
        "pymongo_uri":  str,
        "owners":  str,
        "status":  str,
    }

    def __init__(self, bot):
        self.bot = bot
        self.cache = {}

    def __getitem__(self, config):
        return self.cache[config]

    def load_cache_env(self) -> dict:
        data = deepcopy(Config.bot_config)

        # loads data from enviorment variables
        data.update({k.lower(): self.bot_config[k.lower()](v) for k, v in os.environ.items()
                    if k.lower() in Config.bot_config})

        self.cache = data

        return data

    async def load_cache_db(self, _db):
        db = await _db[self._id].find_one({"_id": self._id})
        if db is None:
            return

        self.cache.update(db)
