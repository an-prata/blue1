# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import datetime
import logging
import os
import requests
from functools import cmp_to_key
from typing import Optional
from . import frc

API_BASE_URL:         str  = 'https://www.thebluealliance.com/api/v3/'
API_TOKEN_ENV_VAR:    str  = 'BLUE1_TBA_API_TOKEN'
API_TOKEN:            str  = os.getenv(API_TOKEN_ENV_VAR)
API_TOKEN_HEADER_KEY: str  = 'X-TBA-Auth-Key'
API_HEADERS:          dict = { API_TOKEN_HEADER_KEY : API_TOKEN }

class Tba:
    token: str


    def __init__(self, token: str):
        self.token = token


    def api_is_up(self) -> bool:
        """
        Returns true if the TBA API is responsive.
        """
        
        return self.get_api_status_json() is not None


    def get_team(self, team_number: int) -> Optional[frc.Team]:
        """
        Gets team info by their team number.
        """
        
        data = self.get_team_json(team_number, simple=False)

        if data is None:
            return None

        return frc.Team(data)


    def get_team_matches(self, team_number: int, event_id: str) -> [frc.Match]:
        """
        Gets a list of matches that the given team played in for the given 
        event by team number and event ID.
        """

        data_matches = self.get_team_matches_json(team_number, event_id=event_id)
        matches: [frc.Match] = [frc.Match(m) for m in data_matches]
        return matches
    

    def get_match(self, match_id: str) -> Optional[frc.Match]:
        """
        Gets a match by its ID string (e.i. 2023cabl_qm1).
        """

        data = self.get_match_json(match_id, simple=False)

        if data is None:
            return None

        return frc.Match(data)


    def get_event(self, event_id: str) -> Optional[frc.Event]:
        """
        Gets an event by its ID string (e.i. 2023cabl).
        """

        data = self.get_event_json(event_id, simple=False)

        if data is None:
            return None

        return frc.Event(data)
    

    def get_event_matches(self, event_id: str) -> [frc.Match]:
        """
        Gets a list of matches from the given event by its ID.
        """

        data_matches = self.get_event_matches_json(event_id)
        matches: [frc.Match] = [frc.Match(m) for m in data_matches]
        return sorted(matches, key=cmp_to_key(frc.match_cmp))

    def get_event_rankings(self, event_id: str) -> [(int, int)]:
        """
        Gets the current team rankings for the given event by its ID.

        Returns a list who's elements are two-tuples, the first item being a
        rank, the second being a team number.
        """

        data = self.get_event_rankings_json(event_id)
        rankings: [(int, int)] = sorted(
            [(r['rank'], frc.team_number_from_id(r['team_key'])) for r in data['rankings']],
            key=lambda r: r[0]
        )
        return rankings


    def get_event_teams(self, event_id: str) -> [int]:
        """
        Gets an event's teams.
        """

        data = self.get_event_teams_json(event_id, simple=True)
        teams: [int] = [team['team_number'] for team in data]
        return teams
    
    
    def get_api_status_json(self) -> Optional[dict]:
        """
        Gets the status of the TBA API.

        Returns a JSON dictionary on success, `None` on failure.
        """

        path = "status"
        res = self.make_api_request(path)
        return res.json() if res_is_good(res) else None


    def get_team_json(self, team_number: int, simple: bool = False) -> Optional[dict]:
        """
        Gets team info for the given team number.

        Returns a JSON dictionary on success, `None` on failure.
        """

        path = f"team/frc{team_number}" + ("/simple" if simple else "")
        res = self.make_api_request(path)
        return res.json() if res_is_good(res) else None
    

    def get_team_status_json(self, team_id: int, year: Optional[int] = None) -> Optional[dict]:
        """
        Gets a team's status, uses the current year if one is not supplied.

        Returns a JSON dictionary on success, `None` on failure.
        """

        year = datetime.date.today().year if year is None else year
        path = f"team/frc{team_id}/events/{year}/statuses"
        res = self.make_api_request(path)
        return res.json() if res_is_good(res) else None


    def get_team_matches_json(self, 
                              team_id: int, 
                              year: Optional[int] = None, 
                              event_id: Optional[str] = None,
                              simple: bool = False
                              ) -> Optional[dict]:
        """
        Gets a team's matches, either by year or event, but not both (event IDs
        have a year build in i.e. 2023cabl is 2023's California Beach Blitz). If
        both arguments are provided the event will be used.

        Returns a JSON dictionary on success, `None` on failure.
        """

        year = datetime.date.today().year if year is None else year
        path = (
            f"team/frc{team_id}"
            + (f"/event/{event_id}/matches" if event_id is not None else f"/matches/{year}")
            + (f"/simple" if simple else "")
        )
        res = self.make_api_request(path)
        return res.json() if res_is_good(res) else None


    def get_team_event_status_json(self, team_id: int, event_id: str) -> Optional[dict]:
        """
        Gets a team's status for the given event by the IDs of both.

        Returns a JSON dictionary on success, `None` on failure.
        """

        path = f"team/frc{team_id}/event/{event_id}/status"
        res = self.make_api_request(path)
        return res.json() if res_is_good(res) else None
    

    def get_event_json(self, event_id: str, simple: bool = False) -> Optional[dict]:
        """
        Gets an event's information by its ID.

        Returns a JSON dictionary on success, `None` on failure.
        """

        path = f"event/{event_id}" + ("/simple" if simple else "")
        res = self.make_api_request(path)
        return res.json() if res_is_good(res) else None


    def get_event_rankings_json(self, event_id: str) -> Optional[dict]:
        """
        Gets the team rankings of an event by its ID.

        Returns a JSON dictionary on success, `None` on failure.
        """

        path = f"event/{event_id}/rankings"
        res = self.make_api_request(path)
        return res.json() if res_is_good(res) else None


    def get_event_teams_json(self, event_id: str, simple: bool = False) -> Optional[dict]:
        """
        Gets an event's team roster by its ID.

        Returns a JSON dictionary on success, `None` on failure.
        """

        path = f"event/{event_id}/teams" + ("/simple" if simple else "")
        res = self.make_api_request(path)
        return res.json() if res_is_good(res) else None


    def get_event_matches_json(self, event_id: str, simple: bool = False) -> Optional[dict]:
        """
        Gets an event's matches by its ID.

        Returns a JSON dictionary on success, `None` on failure.
        """

        path = f"event/{event_id}/matches" + ("/simple" if simple else "")
        res = self.make_api_request(path)
        return res.json() if res_is_good(res) else None
    

    def get_match_json(self, match_id: str, simple: bool = False) -> Optional[dict]:
        """
        Gets match data by its ID.

        Returns a JSON dictionary on success, `None` on failure.
        """

        path = f"match/{match_id}" + ("/simple" if simple else "")
        res = self.make_api_request(path)
        return res.json() if res_is_good(res) else None
    

    def make_api_request(self, path: str) -> requests.Response:
        """
        Make an API request to the given path for TBA, using this instance's
        token.

        This method should be avoided for use outside of the `Tba` class 
        internals.
        """
        
        headers = { API_TOKEN_HEADER_KEY : self.token}
        url = API_BASE_URL + path
        logging.info(f"making request for '{url}'")
        return requests.get(url, headers=headers)


def tba_from_env() -> Tba:
    """
    Creates a new `Tba` with a token derived from an enviornment variable. If
    the required variable is not present, this function logs a critical error
    and exits the program.
    """

    if API_TOKEN is None:
        logging.critical(f"{API_TOKEN_ENV_VAR} enviornment variable not present")
        exit(1)

    return Tba(API_TOKEN)


def res_is_good(res: requests.Response) -> bool:
    """
    Returns true if the response indicates success. If the response indicates
    failure it will be logged as an error.  
    """

    if res.status_code != requests.codes.ok:
        logging.error(f"request to '{res.request.path_url}' failed with code '{res.status_code}'")
        return False

    return True
