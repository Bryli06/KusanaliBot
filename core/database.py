import sys
import motor.motor_asyncio as motor  # motor instead of mongoclient for async
from pymongo.errors import ConfigurationError
from core.logger import get_logger

logger = get_logger(__name__)


class Database:
    def __init__(self, bot):
        self.bot = bot
        self.db = None

        try:
            # gets kusanalibot database in db
            self.db = motor.AsyncIOMotorClient(
                bot.settings["pymongo_uri"]).kusanalibot

        except ConfigurationError as e:
            logger.error(f"MongoDB connection error: {e}")
            sys.exit(0)

        self.session = bot.get_session()

    async def get_collection(self, coll):
        return self.db[coll]

    async def validate_connection(self, *, ssl_retry=True):
        try:
            await self.db.command("buildinfo")
        except Exception as e:
            logger.error("Error with database connection.")
            error = f"{type(e).__name__}: {str(e)}"
            logger.error(error)

            if "CERTIFICATE_VERIFY_FAILED" in error and ssl_retry:
                uri = self.bot.settings["pymongo_uri"]
                logger.critical("Invalid SSL certificate")
                self.db = motor.AsyncIOMotorClient(
                    uri, tlsAllowInvalidCertificates=True).kusanalibot

                return await self.validate_connection(ssl_retry=False)

            if "ServerSelectionTimeoutError" in error:
                logger.critical("IP not whitelisted.")

            if "OperationFailure" in error:
                logger.critical("Invalid credentials.")

            raise

        logger.info("Successful connection.")
