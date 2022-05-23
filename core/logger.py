import sys

import logging
from colorama import Fore, Style


class Logger(logging.Logger):
    def error(self, msg, *args, **kwargs):
        self._log(logging.ERROR, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._log(logging.INFO, msg, args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log(logging.WARNING, msg, args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._log(logging.CRITICAL, msg, args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._log(logging.DEBUG, msg, args, **kwargs)


logging.setLoggerClass(Logger)
loggers = set()
ch = logging.StreamHandler(stream=sys.stdout)
ch.setLevel(logging.INFO)


def get_logger(name):
    logger = logging.getLogger(name)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)
    loggers.add(logger)

    return logger
