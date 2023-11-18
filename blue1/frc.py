# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import functools
from typing import Optional

class Team:
    id:                Optional[str] = None
    name:              Optional[str] = None
    nickname:          Optional[str] = None
    school_name:       Optional[str] = None
    website:           Optional[str] = None
    country:           Optional[str] = None
    state_or_province: Optional[str] = None
    city:              Optional[str] = None

    team_number: Optional[int] = None
    rookie_year: Optional[int] = None


    def __init__(self, json: dict):
        self.id                = json['key']
        self.name              = json['name']
        self.nickname          = json['nickname']
        self.school_name       = json['school_name']
        self.website           = json['website']
        self.country           = json['country']
        self.state_or_province = json['state_prov']
        self.city              = json['city']

        self.team_number = int(json['team_number'])
        self.rookie_year = int(json['rookie_year'])


    def pretty_print(self) -> str:
        return (
            f"Team {self.team_number} is from {self.city}, {self.state_or_province}, {self.country}, " +
            f"and they began competing in {self.rookie_year}. " +
            (f"They go by the name \"{self.nickname}\". " if self.nickname is not None else "") +
            (f"This team also has a website at {self.website}. " if self.website is not None else "") +
            (f"They are a school hosted team at {self.school_name}. " if self.school_name is not None else "")
        )


def team_number_from_id(id: str) -> int:
    return int(id.removeprefix('frc'))


class Event:
    id:         Optional[str]
    name:       Optional[str]
    event_code: Optional[str]
    event_type: Optional[str]
    website:    Optional[str]

    playoff_type: Optional[str]

    country:           Optional[str]
    state_or_province: Optional[str]
    city:              Optional[str]
    address:           Optional[str]
    location_name:     Optional[str]
    gmaps_url:         Optional[str]

    start_date: Optional[str]
    end_date:   Optional[str]
    year:       Optional[int]


    def __init__(self, json: dict):
        self.id         = json['key']
        self.name       = json['name']
        self.event_code = json['event_code']
        self.event_type = json['event_type_string']
        self.website    = json['website']

        self.playoff_type = json['playoff_type_string']
        
        self.country           = json['country']
        self.state_or_province = json['state_prov']
        self.city              = json['city']
        self.address           = json['address']
        self.location_name     = json['location_name']
        self.gmaps_url         = json['gmaps_url']

        self.start_date = json['start_date']
        self.end_date   = json['end_date']
        self.year       = int(json['year'])


    def pretty_print(self) -> str:
        return (
            f"{self.name} ({self.id}) is a(n) {self.event_type} event with {self.playoff_type} playoffs " +
            f"at {self.location_name}. It begins {self.start_date} and end {self.end_date} for {self.year}. " +
            f"Its address is {self.address} and it can be viewed on Google Maps here: {self.gmaps_url}.\n" +
            f"Happy competing! :D"
        )


class Match:
    id:           Optional[str]
    event_id:     Optional[str]
    comp_level:   Optional[str]
    set_number:   Optional[int]
    match_number: Optional[int]

    red_alliance_teams:  [int]
    blue_alliance_teams: [int]

    red_alliance_score:  Optional[int]
    blue_alliance_score: Optional[int]

    red_alliance_rp_awarded:  Optional[int]
    blue_alliance_rp_awarded: Optional[int]

    red_alliance_score_breakdown:  Optional[dict]
    blue_alliance_score_breakdown: Optional[dict]

    winning_alliance: Optional[str]

    videos: Optional[dict]
    

    def __init__(self, json: dict):
        self.id           = json['key']
        self.event_id     = json['event_key']
        self.comp_level   = json['comp_level']
        self.set_number   = json['set_number']
        self.match_number = json['match_number']

        self.red_alliance_teams  = [team_number_from_id(id) for id in json['alliances']['red']['team_keys']]
        self.blue_alliance_teams = [team_number_from_id(id) for id in json['alliances']['blue']['team_keys']]

        self.red_alliance_score  = int(json['alliances']['red']['score'])
        self.blue_alliance_score = int(json['alliances']['blue']['score'])

        self.red_alliance_rp_awarded  = int(json['score_breakdown']['red']['rp'])
        self.blue_alliance_rp_awarded = int(json['score_breakdown']['blue']['rp'])

        self.red_alliance_score_breakdown  = json['score_breakdown']['red']
        self.blue_alliance_score_breakdown = json['score_breakdown']['blue']

        self.winning_alliance = json['winning_alliance']

        self.videos = json['videos']


    def pretty_print(self) -> str:
        r1 = self.red_alliance_teams[0]
        r2 = self.red_alliance_teams[1]
        r3 = self.red_alliance_teams[2]

        b1 = self.blue_alliance_teams[0]
        b2 = self.blue_alliance_teams[1]
        b3 = self.blue_alliance_teams[2]

        video_urls_list = [f"https://youtube.com/watch?v={v['key']}" for v in self.videos if v['type'] == 'youtube']
        video_urls_str = functools.reduce(lambda acc, i: f"{acc}, {i}", video_urls_list, '')

        return (
            f"Match {self.comp_level} {self.match_number} of {self.event_id}:\n" +
            f"Blue Alliance: {b1}, {b2}, {b3} vs Red Alliance: {r1}, {r2}, {r3}\n" +
            f"Score: {self.blue_alliance_score} (Blue) - {self.red_alliance_score} (Red)\n" +
            f"RP Awarded: {self.blue_alliance_rp_awarded} (Blue) - {self.red_alliance_rp_awarded} (Red)\n" +
            (f"Vidoe(s) of the match can be found here: {video_urls_str}" if len(video_urls_list) > 0 else "")
        )

