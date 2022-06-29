from threading import Thread
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

        # loading private config variables
        self.config = Config(self)
        self.config.load_cache_env()

        self.session = None
        self.connected = asyncio.Event()

        # fetching the online database
        self.api = Database(self)
        self.db = self.api.db

        # loading public config variables
        self.loop.create_task(self.config.load_cache_db(self.db))

        self.start_time = datetime.utcnow()

        self.on_start()

        # counter for done loading cogs tasks, used to determine when to run after_load()
        self.tasks_done = 0

        # wait for tasks to be done
        self.loop.create_task(self.wait_for_tasks())

    def on_start(self):

        # loads the cogs into the bot
        for cog in [file.replace('.py', '') for file in listdir("cogs") if isfile(join('cogs', file))]:
            logger.info(f"Loading cog: {cog}")

            try:
                self.load_extension('cogs' + '.' + cog)
                logger.info(f"Successfully loaded {cog}")
            except Exception as e:
                logger.error(f"Failed to load {cog}")
                logger.error(f"Error: {e}")

    async def wait_for_tasks(self):
        # waits until all the loding cogs tasks are done
        while self.tasks_done < len(self.cogs):
            await asyncio.sleep(1)

        await self.after_start()

    async def after_start(self):
        # executes the after_load() method inside cogs
        for cog in self.cogs:
            logger.info(f"Executing after load for: {cog}")

            try:
                await self.cogs[cog].after_load()
                logger.info(f"Successfully executed after load for {cog}")
            except Exception as e:
                logger.error(f"Failed to execute after load for {cog}")
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

                    # try again with members intent
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
        def stop_loop_on_completion():
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


    async def on_ready(self):
        # sets the status of the bot
        await self.change_presence(activity=discord.Activity(
                                    type=discord.ActivityType.watching, name='over the server'))





def main():
    bot = KusanaliBot()
    bot.run()


if __name__ == "__main__":
    main()
