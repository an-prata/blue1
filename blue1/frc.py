# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

from typing import Optional

class Team:
    id:       str
    number:   int
    nickname: Optional[str]


    def __init__(self, number: int, nickname: Optional[str] = None):
        self.id = f"frc{number}"
        self.number = number
        self.nickname = nickname


def team_from_json(json_dict: dict) -> Team:
    """
    Builds a `Team` object from the given JSON.
    """

    return Team(number=json_dict['number'], nickname=json_dict['nickname'])


class Event:
    name: str
    id:   str


    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


def event_from_json(json_dict: dict) -> Event:
    """
    Build an `Event` object from the given JSON.
    """

    return Event(id=json_dict['key'], name=json_dict['name'])
