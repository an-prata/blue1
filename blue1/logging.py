# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import sys
import datetime
from enum import StrEnum

class Color(StrEnum):
    RED    = "\033[31m"
    YELLOW = "\033[33m"
    BLUE   = "\033[34m"
    BOLD   = "\033[1m"
    NORMAL = "\033[0m"
    

def log(id: str, *kargs):
    """
    Log info to stdout.
    """
    
    for arg in kargs:
        time = datetime.datetime.now()
        sys.stdout.write(f"[{Color.BLUE}{Color.BOLD}INFO{Color.NORMAL}] [{time}] [{Color.BOLD}{id}{Color.NORMAL}]: {arg}\n")

def warn(id: str, *kargs):
    """
    Log a warning to stdout.
    """
    
    for arg in kargs:
        time = datetime.datetime.now()
        sys.stdout.write(f"[{Color.YELLOW}{Color.BOLD}WARN{Color.NORMAL}] [{time}] [{Color.BOLD}{id}{Color.NORMAL}]: {arg}\n")

def err(id: str, *kargs):
    """
    Log an error to stderr.
    """
    
    for arg in kargs:
        time = datetime.datetime.now()
        sys.stderr.write(f"[{Color.RED}{Color.BOLD}ERR{Color.NORMAL}]  [{time}] [{Color.BOLD}{id}{Color.NORMAL}]: {arg}\n")

