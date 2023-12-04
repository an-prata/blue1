# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import asyncio
from . import bot
from . import tba
from . import logging

if __name__ == '__main__':
    logging.open_log_file()
    t = tba.tba_from_env()
    b = bot.blue1_from_env(t)
    asyncio.get_event_loop().run_until_complete(b.start())

