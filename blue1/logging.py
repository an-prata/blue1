# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import sys
import datetime
import inspect
import os
from enum import StrEnum
from . import state

LOG_PATH = f"{state.XDG_STATE_HOME}/blue1.log"
LOG_FILE = None

dbg_enabled = False

class Color(StrEnum):
    RED    = "\033[31m"
    YELLOW = "\033[33m"
    BLUE   = "\033[34m"
    BOLD   = "\033[1m"
    NORMAL = "\033[0m"


def open_log_file(path: str=LOG_PATH) -> bool:
    """
    Opens the given file path, or a default file path, to save logs to.
    """

    global LOG_FILE

    try:
        LOG_FILE = open(path, 'a')
        log("LOG", f"Opened '{path}' for logging")
        return True
    except OSError:
        err("LOG", f"Could not open '{path}' for saving logs")
        LOG_FILE = None
        return False
    

def log(id: str, *kargs):
    """
    Log info to stdout.
    """
    
    global LOG_FILE

    for arg in kargs:
        time = datetime.datetime.now()
        sys.stdout.write(f"[{Color.BLUE}{Color.BOLD}INFO{Color.NORMAL}] [{time}] [{Color.BOLD}{id}{Color.NORMAL}]: {arg}\n")

        if LOG_FILE is None:
            continue

        LOG_FILE.write(f"[INFO] [{time}] [{id}]: {arg}\n")
        LOG_FILE.flush()
        

def warn(id: str, *kargs):
    """
    Log a warning to stdout.
    """
    
    global LOG_FILE
    
    for arg in kargs:
        time = datetime.datetime.now()
        sys.stdout.write(f"[{Color.YELLOW}{Color.BOLD}WARN{Color.NORMAL}] [{time}] [{Color.BOLD}{id}{Color.NORMAL}]: {arg}\n")

        if LOG_FILE is None:
            continue

        LOG_FILE.write(f"[WARN] [{time}] [{id}]: {arg}\n")
        LOG_FILE.flush()
        

def err(id: str, *kargs):
    """
    Log an error to stderr.
    """
    
    global LOG_FILE

    for arg in kargs:
        time = datetime.datetime.now()
        sys.stderr.write(f"[{Color.RED}{Color.BOLD}ERR{Color.NORMAL}]  [{time}] [{Color.BOLD}{id}{Color.NORMAL}]: {arg}\n")

        if LOG_FILE is None:
            continue

        LOG_FILE.write(f"[ERR]  [{time}] [{id}]: {arg}\n")
        LOG_FILE.flush()
        

def dbg(data: any) -> any:
    """
    Log a debug message, only prints of debug messages are enabled with 
    `enable_dbg()`. Returns the `data` given. Debug logs are not saved to file.
    """

    global dbg_enabled

    if dbg_enabled:
        time = datetime.datetime.now()
        caller = inspect.stack()[1]
        filename = caller.filename.removeprefix(os.getcwd() + '/')
        line = caller.lineno
        sys.stdout.write(f"[{Color.BOLD}DBG{Color.NORMAL}]  [{time}] ['{filename}' (line {line})]: {data}\n")

    return data


def enable_dbg(enable: bool = True):
    """
    Enables or disables the printing of verbose debug messages to stdout.
    """

    global dbg_enabled

    if not enable:
        dbg(f"Disabled {Color.BOLD}DBG{Color.NORMAL} log")
    
    dbg_enabled = enable

    if enable:
        dbg(f"Enabled {Color.BOLD}DBG{Color.NORMAL} log")
