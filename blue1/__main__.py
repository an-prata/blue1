# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import asyncio
import json
from . import bot
from . import tba

if __name__ == '__main__':
    t = tba.tba_from_env()
    b = bot.blue1_from_env(t)
    asyncio.get_event_loop().run_until_complete(b.start())

