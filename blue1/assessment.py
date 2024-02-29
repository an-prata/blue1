# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

from . import logging
from . import tba

def assess_team(team_num: int, event_id: str) -> str:
    matches = tba.TBA.get_team_matches(team_num, event_id)

    if matches is None or len(matches) < 1:
        return "Could not get data on team " + team_num + " for " + event_id + "."

    scores = []
    total_score = 0
    wins = 0
    games = 0

    for match in matches:
        score = match.get_team_score(team_num)
        won = match.did_team_win(team_num)

        if score is None or won is None:
            continue
        
        games = games + 1
        total_score = total_score + score
        scores.append(score)

        if won:
            wins = wins + 1

    if games < 1:
        return "Team " + team_num + " has not played at " + event_id + " yet."

    variance = max(scores) - min(scores)
    average_score = float(total_score) / float(games)
    win_rate = float(wins) / float(games)
    median_score = scores[int(len(scores) / 2)]

    msg = "Team has a win rate of " + str(win_rate) + " and an average score of " + str(average_score) + ". Their score varied from max to min by " + str(variance) + ". " + "Their median score is " + str(median_score) + "."

    return msg
