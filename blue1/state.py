# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import json
import os
from typing import Callable, Optional
from io import TextIOWrapper

# File and directory paths here based on the XDG Base Directory spec.
# Please RTFM: https://wiki.archlinux.org/title/XDG_Base_Directory

HOME_DIR:        str = os.getenv('HOME')
XDG_STATE_HOME:  str = os.getenv('XDG_STATE_HOME') or f"{HOME_DIR}/.local/state"
XDG_CACHE_HOME:  str = os.getenv('XDG_CACHE_HOME') or f"{HOME_DIR}/.cache"
STATE_FILE_PATH: str = f"{XDG_STATE_HOME}/blue1/state.json"
CACHE_FILE_PATH: str = f"{XDG_CACHE_HOME}/blue1/cache.json"

class FileDictMonad:
    """
    A monad wrapping a `dict` that is repeatadly saved to disk.
    """
    
    state_json: dict
    state_file: str


    def __init__(self, path: str):
        self.state_file = path
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

        # If the file does not exist create it and write an empty json 
        # dictionary to it, otherwise we get json parsing issues.
        if not os.path.exists(self.state_file):
            with open(self.state_file, 'w+') as fp:
                fp.write('{}')

        with open(self.state_file, 'r') as fp:
            self.state_json = json.load(fp)


    def set(self, key: str, value):
        """
        Applies this given function to the internal `dict` of this 
        `FileDictMonad` and writes the changes to file.
        """

        self.state_json[key] = value 

        with open(self.state_file, 'w+') as fp:
            fp.write(json.dumps(self.state_json))


    def get(self, key):
        """
        Gets the value for the given key. Yeilds `None` if the key is not 
        present.
        """

        try:
            return self.state_json[key]
        except:
            return None


STATE = FileDictMonad(STATE_FILE_PATH)
CACHE = FileDictMonad(CACHE_FILE_PATH)
