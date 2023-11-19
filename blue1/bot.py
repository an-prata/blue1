# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import discord
import logging
import json
import os
from time import sleep
from datetime import datetime
from functools import cmp_to_key
from matplotlib import pyplot
from discord.ext import commands
from . import tba
from . import frc

API_TOKEN_ENV_VAR = 'BLUE1_DISCORD_API_TOKEN'
API_TOKEN: str = os.getenv(API_TOKEN_ENV_VAR)
DISCORD_MAX_MESSAGE = 2000

class Blue1:
    bot:      commands.Bot
    token:    str
    tba:      tba.Tba
    plotting: bool = False

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
        async def get_event_matches(ctx, event_id):
            matches = sorted(
                self.tba.get_event_matches(event_id),
                key=cmp_to_key(frc.match_cmp)
            )

            message = [""]
            message_i = 0

            for match in matches:
                if not match.was_played():
                    continue
                
                this_match = f"{match.human_readable_name()}"
                tmp = f"{message[message_i]}\n{this_match}"

                if len(tmp) >= DISCORD_MAX_MESSAGE:
                    message_i += 1
                    message.append(this_match)
                else:
                    message[message_i] = tmp


            for msg in message:
                await ctx.send(msg)
        

        @self.bot.command()
        async def get_team_event(ctx, team_number, event_id):
            team_number = int(team_number)
            matches = sorted(
                self.tba.get_team_matches(
                    team_number, 
                    event_id=event_id
                ), 
                key=cmp_to_key(frc.match_cmp)
            )

            if len(matches) < 1:
                await ctx.send(f"no matched for {team} at {event_id}")
                return

            team_scores: [float] = []

            message = [""]
            message_i = 0

            for match in matches:
                if not match.was_played():
                    continue
                
                this_match = f"{match.pretty_print()}"
                tmp = f"{message[message_i]}\n{this_match}"

                if len(tmp) >= DISCORD_MAX_MESSAGE:
                    message_i += 1
                    message.append(this_match)
                else:
                    message[message_i] = tmp

                team_scores.append(match.get_team_score(team_number))
            
            while self.plotting:
                sleep(0.25)

            # deny plotting to other async calls to this method
            self.plotting = True

            file_name = f"/tmp/blue1-{datetime.now().strftime('%M%I%S%f')}.png"
            
            pyplot.plot(team_scores, linewidth=2, color='blue')
            pyplot.plot(team_scores, 'o', color='blue')
            pyplot.xlabel('matches played')
            pyplot.ylabel(f"team {team_number}'s score")
            pyplot.xticks(range(1, len(team_scores) + 1))

            _, upper = pyplot.ylim()
            pyplot.ylim(0, upper)

            pyplot.savefig(file_name)
            pyplot.clf()

            # allow plotting by other async calls of this metho
            self.plotting = False
            
            for m in message:
                await ctx.send(m)
                
            await ctx.send("", file=discord.File(file_name))
            os.remove(file_name)


        @self.bot.command()
        async def compare_teams_event(ctx, team1_number, team2_number, event_id):
            team1_number = int(team1_number)
            team2_number = int(team2_number)

            team1_matches = sorted(
                self.tba.get_team_matches(team1_number, event_id),
                key=cmp_to_key(frc.match_cmp)
            )

            team2_matches = sorted(
                self.tba.get_team_matches(team2_number, event_id),
                key=cmp_to_key(frc.match_cmp)
            )

            event_matches = sorted(
                self.tba.get_event_matches(event_id),
                key=cmp_to_key(frc.match_cmp)
            )

            qualifiers: [Match] = [m for m in event_matches if 'qm' in m.comp_level]
            semifinals: [Match] = [m for m in event_matches if 'sf' in m.comp_level]
            team1_scores: [int] = [m.get_team_score(team1_number) for m in team1_matches if m.was_played()]
            team2_scores: [int] = [m.get_team_score(team2_number) for m in team2_matches if m.was_played()]

            scale = lambda m: (
                m.overall_number() + 
                (qualifiers[-1].overall_number() if 'qm' not in m.comp_level else 0) +
                (semifinals[-1].overall_number() if 'sf' not in m.comp_level and 'qm' not in m.comp_level else 0)
            )
            
            team1_match_numbers: [int] = [scale(m) for m in team1_matches if m.was_played()]
            team2_match_numbers: [int] = [scale(m) for m in team2_matches if m.was_played()]

            while self.plotting:
                sleep(0.25)

            # deny plotting to other async calls to this method
            self.plotting = True

            file_name = f"/tmp/blue1-{datetime.now().strftime('%M%I%S%f')}.png"
            
            pyplot.plot(team1_match_numbers, team1_scores, linewidth=2, color='blue')
            pyplot.plot(team1_match_numbers, team1_scores, 'o', color='blue',)
            pyplot.plot(team2_match_numbers, team2_scores, linewidth=2, color='red')
            pyplot.plot(team2_match_numbers, team2_scores, 'o', color='red',)
            pyplot.xlabel('match number')
            pyplot.ylabel(f"scores (team one in red, two in blue)")
            pyplot.xticks(range(0, len(event_matches) + 1, 10))

            _, upper = pyplot.ylim()
            pyplot.ylim(0, upper)
            
            pyplot.savefig(file_name)
            pyplot.clf()

            # allow plotting by other async calls of this method
            self.plotting = False
                
            await ctx.send("", file=discord.File(file_name))
            os.remove(file_name)
            

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
