import discord
from discord.ext import commands

import sys

from os import listdir
from os.path import isfile, join

import asyncio
from aiohttp import ClientSession
from datetime import datetime
from core.logger import get_logger

from core.database import Database
from core.config import Config

logger = get_logger(__name__)


class KusanaliBot(commands.Bot):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.config = Config(self)
        self.config.load_cache_env()

        self.session = None
        self.api = Database(self)
        self.db = self.api.db
        self.connected = asyncio.Event()

        self.loop.create_task(self.config.load_cache_db(self.db))

        self.start_time = datetime.utcnow()
        self.on_start()

    async def on_application_command_error(self, ctx: discord.ApplicationContext, exception: discord.DiscordException):
        embed = discord.Embed(title="Error",
                              description=f"It seems an error has occured.\nError:`{exception}`\nIf you believe this to be a bug please report it to the technical mod team.")

        await ctx.respond(embed=embed)

    def on_start(self):
        for cog in [file.replace('.py', '') for file in listdir("cogs") if isfile(join('cogs', file))]:
            logger.info(f"Loading cog: {cog}")

            try:
                self.load_extension('cogs' + '.' + cog)
                logger.info(f"Successfully loaded {cog}")
            except Exception as e:
                logger.error(f"Failed to load {cog}")
                logger.error(f"Error: {e}")

    async def get_session(self):
        if self.session is None:
            self.session = ClientSession(loop=self.loop)
        return self.session

    def run(self):
        loop = self.loop

        async def runner():
            try:
                retry_intents = False
                try:
                    await self.start(self.config["bot_token"])
                except discord.PrivilegedIntentsRequired:
                    retry_intents = True
                if retry_intents:
                    await self.http.close()
                    if self.ws is not None and self.ws.open:
                        await self.ws.close(code=1000)
                    self._ready.clear()
                    intents = discord.Intents.default()
                    intents.members = True
                    # Try again with members intent
                    self._connection._intents = intents
                    logger.warning(
                        "Attempting to login with only the server members privileged intent. Some plugins might not work correctly."
                    )
                    await self.start(self.token)
            except discord.PrivilegedIntentsRequired:
                logger.critical(
                    "Privileged intents are not explicitly granted in the discord developers dashboard."
                )
            except discord.LoginFailure:
                logger.critical("Invalid token")
            except Exception:
                logger.critical("Fatal exception", exc_info=True)
            finally:
                if not self.is_closed():
                    await self.close()
                if self.session:
                    await self.session.close()

        # noinspection PyUnusedLocal
        def stop_loop_on_completion(f):
            loop.stop()

        def _cancel_tasks():
            task_retriever = asyncio.all_tasks

            tasks = {t for t in task_retriever(loop=loop) if not t.done()}

            if not tasks:
                return

            logger.info("Cleaning up after %d tasks.", len(tasks))
            for task in tasks:
                task.cancel()

            loop.run_until_complete(asyncio.gather(
                *tasks, return_exceptions=True))
            logger.info("All tasks finished cancelling.")

            for task in tasks:
                if task.cancelled():
                    continue
                if task.exception() is not None:
                    loop.call_exception_handler(
                        {
                            "message": "Unhandled exception during Client.run shutdown.",
                            "exception": task.exception(),
                            "task": task,
                        }
                    )

        future = asyncio.ensure_future(runner(), loop=loop)
        future.add_done_callback(stop_loop_on_completion)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Received signal to terminate bot and event loop.")
        finally:
            future.remove_done_callback(stop_loop_on_completion)
            logger.info("Cleaning up tasks.")

            try:
                _cancel_tasks()
                if sys.version_info >= (3, 6):
                    loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                logger.info("Closing the event loop.")

        if not future.cancelled():
            try:
                return future.result()
            except KeyboardInterrupt:
                # I am unsure why this gets raised here but suppress it anyway
                return None


def main():
    try:
        # noinspection PyUnresolvedReferences
        import uvloop

        logger.debug("Setting up with uvloop.")
        uvloop.install()
    except ImportError:
        pass

    bot = KusanaliBot()
    bot.run()


if __name__ == "__main__":
    main()
