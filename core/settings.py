from copy import deepcopy
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:

    bot_config = {
        "prefix": ".",
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

    def load_cache(self) -> dict:
        data = deepcopy(Settings.bot_config)

        data.update({k.lower(): v for k, v in os.environ.items() if k.lower() in Settings.bot_config}) # loads data from enviormental variables
       
        self.cache = data
        # add load from db
        return data
    def load(self) -> dict:
        pass #implement load data from db 

