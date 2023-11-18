# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import discord
import logging
import json
import os
from matplotlib import pyplot
from discord.ext import commands
from . import tba

API_TOKEN_ENV_VAR = 'BLUE1_DISCORD_API_TOKEN'
API_TOKEN: str = os.getenv(API_TOKEN_ENV_VAR)

class Blue1:
    bot:   commands.Bot
    token: str
    tba:   tba.Tba

    def __init__(self, token: str, tba: tba.Tba):
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix='&', intents=intents)
        self.token = token
        self.tba = tba


        @self.bot.command()
        async def get_team(ctx, team):
            data = self.tba.get_team(int(team))
            await ctx.send(data.pretty_print())


        @self.bot.command()
        async def get_match(ctx, match_id):
            match = self.tba.get_match(match_id)
            await ctx.send(match.pretty_print())


        @self.bot.command()
        async def get_event(ctx, event_id):
            event = self.tba.get_event(event_id)
            await ctx.send(event.pretty_print())
        

        @self.bot.command()
        async def get_team_event(ctx, team, event):
            team = int(team)
            matches = self.tba.get_team_matches_json(team, event_id=event)

            if matches is None:
                await ctx.send(f"could not get data on {team} for event")
                return


            def match_index(match) -> int:
                index = int(match['match_number'])

                if match['comp_level'] == 'sf':
                    index += 250
                elif match['comp_level'] == 'f':
                    index += 300

                return index
            

            team_scores: [float] = []
            opponent_scores: [float] = []

            matches_in_msg = 0
            msg = ""

            for match in sorted(matches, key=match_index):
                number = match['match_number']
                level = match['comp_level']
                red_alliance = match['alliances']['red']['team_keys']
                red_score = match['alliances']['red']['score']
                blue_alliance = match['alliances']['blue']['team_keys']
                blue_score = match['alliances']['blue']['score']
                msg = f"""{msg}
**Match {level} {number}**:
*:blue_circle: Blue Alliance*: {blue_alliance}
*:blue_circle: Blue Alliance Score*: {blue_score}
*:red_circle: Red Alliance*: {red_alliance}
*:red_circle: Red Alliance Score*: {red_score}
                """
                matches_in_msg += 1

                if matches_in_msg >= 4:
                    await ctx.send(msg)
                    msg = ""
                    matches_in_msg = 0

                if f"frc{team}" in red_alliance:
                    team_scores.append(float(red_score))
                    opponent_scores.append(float(blue_score))
                else:
                    team_scores.append(float(blue_score))
                    opponent_scores.append(float(red_score))
            
            pyplot.plot(team_scores, linewidth=6)
            pyplot.xlabel('matches played')
            pyplot.ylabel(f"team {team}'s score")
            pyplot.savefig('temp.png')
            
            await ctx.send("", file=discord.File('temp.png'))
            os.remove('temp.png')
            

    async def start(self):
        await self.bot.start(self.token, reconnect=True)
        

def blue1_from_env(tba: tba.Tba) -> Blue1:
    """
    Creates a new `Blue1` with a token derived from an enviornment variable. If
    the required variable is not present, this function logs a critical error
    and exits the program.
    """

    if API_TOKEN is None:
        logging.critical(f"{API_TOKEN_ENV_VAR} enviornment variable not present")
        exit(1)

    return Blue1(API_TOKEN, tba)
