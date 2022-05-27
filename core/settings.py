from copy import deepcopy
import os
from dotenv import load_dotenv

load_dotenv()

guild_id = os.getenv("GUILD_ID")
class Settings:

    bot_config = {
        "log": "",
        "pymongo_uri": None,
        "bot_token": None,
        "owners": None,
        "status": "",
        "activity_type": None,
    }

    def __init__(self, bot):
        self.bot = bot
        self.cache = {}

    def __getitem__(self, setting):
        return self.cache[setting]


    def load_cache(self) -> dict:
        data = deepcopy(Settings.bot_config)

        # loads data from enviorment variables
        data.update({k.lower(): v for k, v in os.environ.items()
                    if k.lower() in Settings.bot_config})

        self.cache = data

        return data
