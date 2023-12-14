# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

from enum import StrEnum, auto
from typing import Optional
from . import tba
from . import sheets
from . import logging


class EventType(StrEnum):
    RANK_CHANGED = auto()
    MATCH_SCOUTED = auto()


class EventOptions:
    """
    Details what events of all those avaiable to subscribe to.

    Attributes:
        type  The type of event to subscribe to.
        team  Only produces an event if the event's informaton pretains to this 
              team. If a value is given `MATCH_SCOUTED` will only produce events
              for matches scouted for team in the next match the given team is 
              in. `RANK_CHANGED` events will only be produced if the given 
              team's rank has changed.
    """

    type: EventType
    frc_event: str
    team: Optional[int]


    def __init__(self, type: EventType, frc_event: str, team: Optional[int]):
        self.type = type
        self.frc_event = frc_event
        self.team = team


class EventManager:
    """
    Manages events and exposes a method to be called in a loop in order to
    check for events, produces them, and call subscribing objects.
    """

    subscribers = []
    prev_state: dict = {}
    

    def subscribe(self, event: EventOptions):
        """
        Subscribe a new function to the given event.
        """
        
        logging.dbg(f"Appending subscriber to event manager ...")
        self.subscribers.append(event)
        logging.dbg(f"Setting previous state to `None`")
        self.prev_state[event] = None


    def produce_events(self) -> list:
        """
        Runs event loop code, producing events and returning a list of 
        tuples, the first item is the `EventOptions` that produced the event and
        the second is a dictionaryw which represents the current state that 
        triggered the event.
        """
        
        event_states = []
        
        for opts in self.subscribers:
            curr_state = get_event_state(opts)

            if should_produce_event(opts, self.prev_state[opts], curr_state):
                self.prev_state[opts] = curr_state
                event_states.append((opts, curr_state))

        return event_states

def should_produce_event(event: EventOptions, prev_state: dict, curr_state: dict):
    """
    Returns true if the options for the event, and the change in state, warrant
    producing an event.
    """
    
    if prev_state == curr_state or curr_state is None:
        return False

    if prev_state is None or event.team is None:
        return True

    if event.type == EventType.RANK_CHANGED:
        return prev_state[event.team] != curr_state[event.team]
    elif event.type == EvenType.MATCH_SCOUTED:
        data = tba.TBA.get_team_matches(event.team, event.frc_event)

        if data is None:
            return False

        for match in data:
            if not match.was_played():
                return match.contains_opponent(event.team, int(prev_state['Team Number']))


def get_event_state(event: EventOptions) -> dict:
    """
    Gets the state for a given event.
    """

    if event.type == EventType.RANK_CHANGED:
        rankings_list = tba.TBA.get_event_rankings(event.frc_event)
        rankings = { v: k for (k, v) in rankings_list }
        return rankings
    elif event.type == EventType.MATCH_SCOUTED:
        try:
            sheet = sheets.active_sheets[event.frc_event]
            bounds = sheet.get_sheet_bounds()
            (row, _) = bounds
            return sheet.get_row_dict(row, bounds)
        except:
            return {}
