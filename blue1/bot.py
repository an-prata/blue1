# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import discord
import json
import math
import os
from collections import OrderedDict
from datetime import datetime, timedelta
from discord.ext import commands
from functools import cmp_to_key, reduce
from matplotlib import pyplot
from time import sleep
from typing import Optional
from . import frc
from . import tba
from . import state
from . import sheets
from . import data
from . import logging

API_TOKEN_ENV_VAR = 'BLUE1_DISCORD_API_TOKEN'
API_TOKEN: str = os.getenv(API_TOKEN_ENV_VAR)
DISCORD_MAX_MESSAGE = 2000

class Blue1:
    bot:          commands.Bot
    token:        str
    tba:          tba.Tba
    event_sheets: dict = {}
    plotting:     bool = False

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
        async def get_team_rank(ctx, team_number, event_id):
            team_number = int(team_number)
            teams = self.tba.get_event_teams(event_id)
            matches = sorted(
                self.tba.get_event_matches(event_id),
                key=cmp_to_key(frc.match_cmp)
            )

            # team : (rank points, matches played)
            team_ranks: {int : (int, int)} = OrderedDict({t: (0, 0) for t in teams})
            rp_avg_v_time: [int] = []
            rank_v_time: [int] = []

            for match in matches:
                if match.comp_level != 'qm':
                    continue
                
                for team in match.red_alliance_teams:
                    rp = team_ranks[team][0] + match.red_alliance_rp_awarded
                    matches = team_ranks[team][1] + 1
                    team_ranks[team] = (rp, matches)

                for team in match.blue_alliance_teams:
                    rp = team_ranks[team][0] + match.blue_alliance_rp_awarded
                    matches = team_ranks[team][1] + 1
                    team_ranks[team] = (rp, matches)

                team_ranks = OrderedDict(sorted(
                    team_ranks.items(),
                    key=lambda rank: (
                        float(rank[1][0]) / float(rank[1][1]) if rank[1][1] != 0 else 0
                    )
                ))

                rank = team_ranks[team_number]
                rp_avg_v_time.append(float(rank[0]) / float(rank[1]) if rank[1] != 0 else 0)

                curr_rank: int = 1

                for team, rank in team_ranks.items():
                    team_r = float(rank[0]) / float(rank[1]) if rank[1] != 0 else 0

                    if team_r > rp_avg_v_time[-1]:
                        curr_rank += 1
                    
                # negate to display lesser value ranks higher
                rank_v_time.append(curr_rank)

            while self.plotting:
                sleep(0.25)

            # deny plotting to other async calls to this method
            self.plotting = True

            file1_name = f"/tmp/blue1-{datetime.now().strftime('%M%I%S%f')}.png"
            
            pyplot.plot(range(1, len(rank_v_time) + 1), rank_v_time, linewidth=2, color='blue')
            pyplot.xlabel('qualifying match number')
            pyplot.ylabel(f"team {team_number}'s rank")
            pyplot.xticks(range(0, len(rank_v_time), 10))

            _, upper = pyplot.ylim()
            pyplot.ylim(upper, 0)

            pyplot.savefig(file1_name)
            pyplot.clf()

            file2_name = f"/tmp/blue1-{datetime.now().strftime('%M%I%S%f')}.png"
            
            pyplot.plot(range(1, len(rp_avg_v_time) + 1), rp_avg_v_time, linewidth=2, color='blue')
            pyplot.xlabel('qualifying match number')
            pyplot.ylabel(f"team {team_number}'s average RP award")
            pyplot.xticks(range(0, len(rp_avg_v_time), 10))

            _, upper = pyplot.ylim()
            pyplot.ylim(0, upper)

            pyplot.savefig(file2_name)
            pyplot.clf()

            # allow plotting by other async calls of this metho
            self.plotting = False

            await ctx.send("", file=discord.File(file1_name))
            await ctx.send("", file=discord.File(file2_name))
            os.remove(file1_name)
            os.remove(file2_name)


        @self.bot.command()
        async def get_event_rankings(ctx, event_id):
            rankings = self.tba.get_event_rankings(event_id)
            message = "Rank:\tTeam Number"

            for r, t in rankings:
                pad = ' ' * (3 - int(math.log10(r)))
                message = f"{message}\n{pad}{r}:\t{t}"

            await ctx.send(f"```\n{message}\n```")


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

            team_scores: [int] = []

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
            logging.log("BOT", "Reserving PyPlot ...")
            self.plotting = True

            file_name = f"/tmp/blue1-{datetime.now().strftime('%M%I%S%f')}.png"
            
            pyplot.plot(range(1, len(team_scores) + 1), team_scores, linewidth=2, color='blue')
            pyplot.plot(range(1, len(team_scores) + 1), team_scores, 'o', color='blue')
            pyplot.xlabel('matches played')
            pyplot.ylabel(f"team {team_number}'s score")
            pyplot.xticks(range(1, len(team_scores) + 1))

            _, upper = pyplot.ylim()
            pyplot.ylim(0, upper)

            pyplot.savefig(file_name)
            pyplot.clf()

            # allow plotting by other async calls of this metho
            logging.log("BOT", "Releasing PyPlot ...")
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
            logging.log("BOT", "Reserving PyPlot ...")
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
            logging.log("BOT", "Releasing PyPlot ...")
            self.plotting = False
                
            await ctx.send("", file=discord.File(file_name))
            os.remove(file_name)


        @self.bot.command()
        async def get_cache_hit_rate(ctx):
            rate = float(self.tba.cache_hits) / float(self.tba.cache_misses + self.tba.cache_hits)
            await ctx.send(f"Cache hit rate is {round(rate, 4) * 100}%")
        

        @self.bot.command()
        async def get_scouting_fields(ctx, event):
            sheet = self.get_event_sheet(event)
            
            if sheet is None:
                await ctx.send(
                    f"No scouting spreadsheet has been set for `{event}`, " +
                    'have a priviledged user use the ' + 
                    f"`&set_scouting_sheet {event} [sheet_id]` command"
                )
                return

            bounds = sheet.get_sheet_bounds()
            fields = sheet.get_fields(bounds)
            message = ''

            for field in fields:
                message = f"{message}\n{field}"

            await ctx.send(
                f"These are the available fields from your scouting data:\n" +
                f"```\n{message}\n```"
            )
        

        @self.bot.command()
        async def match_breakdown(ctx, event, match_number, team_number):
            sheet = self.get_event_sheet(event)
            
            if sheet is None:
                await ctx.send(
                    f"No scouting spreadsheet has been set for `{event}`, " +
                    'have a priviledged user use the ' + 
                    f"`&set_scouting_sheet {event} [sheet_id]` command"
                )
                return

            bounds = sheet.get_sheet_bounds()
            fields = sheet.get_fields(bounds)

            teams_col_number = sheets.column_num_to_alpha(fields.index(data.TEAM_FIELD))
            matches_col_number = sheets.column_num_to_alpha(fields.index(data.MATCH_FIELD))

            teams_col = sheet.get_column_list(teams_col_number, bounds)
            matches_col = sheet.get_column_list(matches_col_number, bounds)

            team_match_row = (
                zip(teams_col, matches_col)
                .index(
                    (team_number, match_number)
                )
            ) + 1 # Add one since both lists exclude the first row

            row_dict = sheet.get_row_dict(int(team_match_row), bounds)
            message = ''

            for k, v in row_dict:
                message = f"{message}\n{k}: {v}"

            await ctx.send(message)
                    

        @self.bot.command()
        async def set_scouting_sheet(ctx, event, sheet_id):
            if not await check_priviledges(ctx):
                return

            creds = sheets.produce_valid_credentials()
            service = sheets.get_sheets_service(creds)
            self.event_sheets[event] = sheets.Spreadsheet(service, sheet_id)
            
            state.STATE.set(f"scouting_sheet_id_{event}", sheet_id)
            logging.log("BOT", f"Set scouting sheet for '{event}' to '{sheet_id}'")
            await ctx.send(f"Set scouting spreadsheet id to {sheet_id} for {event}")
        

        @self.bot.command()
        async def set_cache_expiration_time(ctx, time, unit):
            if not await check_priviledges(ctx):
                return
            
            delta: timedelta

            if unit == 'days' or unit == 'day' or unit == 'd':
                delta = int(time) * 24 * 60 * 60
                await ctx.send(f"Setting expiration time to {int(time)} days")
            elif unit == 'hours' or unit == 'hour' or unit == 'h':
                delta = int(time) * 60 * 60
                await ctx.send(f"Setting expiration time to {int(time)} hours")
            elif unit == 'minutes' or unit == 'minute' or unit == 'm':
                delta = int(time) * 60
                await ctx.send(f"Setting expiration time to {int(time)} minutes")
            elif unit == 'seconds' or unit == 'second' or unit == 's':
                delta = int(time)
                await ctx.send(f"Setting expiration time to {int(time)} seconds")
            else:
                await ctx.send(
                    f"Did not recognize unit \"{unit}\"\n" +
                    f"Expected `&set_cache_expiration_date [time] [unit]`\n" +
                    f"where unit is one of `days`, `hours`, `minutes`, or `seconds`\n" +
                    f"or any singular or single letter abbreviation of them."
                )

            state.STATE.set('cache_expiration_time', delta)
            logging.log("BOT", f"Set cache expiration time to {delta} seconds")


    async def start(self):
        await self.bot.start(self.token, reconnect=True)


    def get_event_sheet(self, event: str) -> Optional[sheets.Spreadsheet]:
        """
        Get an event's scouting spreadsheet if it has been saved, otherwise 
        produce it from a sheet ID if it has been set. If both options fail this
        method returns `None`.
        """
        try:
            return self.event_sheets[event]
        except:
            pass

        id = state.STATE.get(f"scouting_sheet_id_{event}")

        if id is None:
            return None

        creds = sheets.produce_valid_credentials()
        service = sheets.get_sheets_service(creds)
        sheet = sheets.Spreadsheet(service, id)
        self.event_sheets[event] = sheet
        return sheet
        

def blue1_from_env(tba: tba.Tba) -> Blue1:
    """
    Creates a new `Blue1` with a token derived from an enviornment variable. If
    the required variable is not present, this function logs a critical error
    and exits the program.
    """

    logging.log("BOT", "Getting Discord API key from enviorment ...")

    if API_TOKEN is None:
        logging.err("BOT", f"{API_TOKEN_ENV_VAR} enviornment variable not present")
        exit(1)

    logging.log("BOT", "Got Discord API key from enviorment")
    return Blue1(API_TOKEN, tba)

async def check_priviledges(ctx):
    priviledged = False

    for role in ctx.author.roles:
        if role.name == 'Blue1 Priviledged':
            priviledged = True
            continue

    if not priviledged:
        logging.warn("BOT", "Attempt to use priviledged command by unpriviledged user")
        await ctx.send('You need to have the Blue1 priviledged role to use this command')
        return False

    return True
