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

            if data is None:
                await ctx.send(f"Could not find team `{team}`")
            else:
                await ctx.send(data.pretty_print())


        @self.bot.command()
        async def get_match(ctx, match_id):
            match = self.tba.get_match(match_id)

            if match is None:
                await ctx.send(f"Could not find match `{match_id}`")
            else:
                await ctx.send(match.pretty_print())


        @self.bot.command()
        async def get_event(ctx, event_id):
            event = self.tba.get_event(event_id)

            if event is None:
                await ctx.send(f"Could not find match `{event_id}`")
            else:
                await ctx.send(event.pretty_print())


        @self.bot.command()
        async def get_team_rank(ctx, team_number, event_id):
            team_number = int(team_number)
            teams = self.tba.get_event_teams(event_id)
            matches_list = self.tba.get_event_matches(event_id)

            if teams is None or matches_list is None:
                await ctx.send(f"Could not find event `{event_id}`")
                return

            matches = sorted(
                matches_list,
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

            await self.plot_line(ctx, rank_v_time, 'qualifying match number', f"team {team_number}'s rank", ticks=range(0, len(rp_avg_v_time), 10))
            await self.plot_line(ctx, rp_avg_v_time, 'qualifying match number', f"team {team_number}'s average RP award", ticks=range(0, len(rp_avg_v_time), 10))


        @self.bot.command()
        async def get_event_rankings(ctx, event_id):
            rankings = self.tba.get_event_rankings(event_id)

            if rankings is None:
                await ctx.send(f"Could not find event `{event_id}`")
                return
            
            message = "Rank:\tTeam Number"

            for r, t in rankings:
                pad = ' ' * (3 - int(math.log10(r)))
                message = f"{message}\n{pad}{r}:\t{t}"

            await ctx.send(f"```\n{message}\n```")


        @self.bot.command()
        async def get_event_matches(ctx, event_id):
            matches_list = self.tba.get_event_matches(event_id)

            if matches_list is None:
                await ctx.send(f"Could not find event `{event_id}`")
                return
            
            matches = sorted(
                matches_list,
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
            matches_list = self.tba.get_team_matches(
                team_number, 
                event_id=event_id
            )

            if matches_list is None:
                await ctx.send(f"Team `{team_number}` does not exist, did not attend event `{event_id}`, or could not find event `{event_id}`")
                return
            
            matches = sorted(
                matches_list, 
                key=cmp_to_key(frc.match_cmp)
            )

            if len(matches) < 1:
                await ctx.send(f"No matches for `{team}` at `{event_id}`")
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
            
            for m in message:
                await ctx.send(m)
                
            await self.plot_line(ctx, team_scores, 'matches played', f"team {team_number}'s score")


        @self.bot.command()
        async def compare_teams_event(ctx, team1_number, team2_number, event_id):
            team1_number = int(team1_number)
            team2_number = int(team2_number)

            team1_matches_list = self.tba.get_team_matches(team1_number, event_id)
            team2_matches_list = self.tba.get_team_matches(team2_number, event_id)
            event_matches_list = self.tba.get_event_matches(event_id)

            if event_matches_list is None:
                await ctx.send(f"Could not find event `{event_id}`")
                return
            
            if team1_matches_list is None:
                await ctx.send(f"Team `{team1_number}` does not exist or did not attend event `{event_id}`")
                return
            
            if team2_matches_list is None:
                await ctx.send(f"Team `{team2_number}` does not exist or did not attend event `{event_id}`")
                return

            team1_matches = sorted(
                team1_matches_list,
                key=cmp_to_key(frc.match_cmp)
            )

            team2_matches = sorted(
                team2_matches_list,
                key=cmp_to_key(frc.match_cmp)
            )

            event_matches = sorted(
                event_matches_list,
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
        async def plot_scouting_field(ctx, event, team_number, field):
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

            if field not in fields:
                await ctx.send(f"`{field}` not found in scouting data.\nUse `&get_scouting_fields [event_id]` to see avaiable fields.")
                return

            teams_col_number = sheets.column_num_to_alpha(fields.index(data.TEAM_FIELD) + 1)
            teams_col = sheet.get_column_list(teams_col_number, bounds)
            field_data = (
                # Add two becuase we get a 0 based index and the sheet is 1 
                # indexed, and because the top row is not data, just labels.
                [sheet.get_row_dict(r + 2, bounds)[field]
                    for r in range(len(teams_col)) if teams_col[r] == team_number ]
            )
            field_data = [0 if x is None or x == '' else int(x) for x in field_data]

            await self.plot_line(ctx, field_data, 'matches played', f"`{field}`")
            
        
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

            teams_col_number = sheets.column_num_to_alpha(fields.index(data.TEAM_FIELD) + 1)
            matches_col_number = sheets.column_num_to_alpha(fields.index(data.MATCH_FIELD) + 1)

            teams_col = sheet.get_column_list(teams_col_number, bounds)
            matches_col = sheet.get_column_list(matches_col_number, bounds)

            team_match_row: Optional[int]

            for i in range(len(teams_col)):
                if teams_col[i] == team_number and matches_col[i] == match_number:
                    team_match_row = i + 1
                    break
                else:
                     team_match_row = None

            if team_match_row is None:
                await ctx.send(f"Could not find match `{match_number}`, or `{team_number}` didn't play that match.\nKeep in mind that your scouting sheet may call matches different names than TBA does.")
                return
            else:
                team_match_row += 1

            row_dict = sheet.get_row_dict(int(team_match_row), bounds)
            message = ''

            for k, v in row_dict.items():
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


        @self.bot.command()
        async def print_help(ctx):
            help0 = (
                "To use `blue1` command prefix them with `&`, here are the avaiable commands:\n"
                + "`&get_team [team_number]` - Gets basic team info given their number\n"
                + "`&get_match [match_id]` - Gets match info, `[match_id]` is in the format `2023cabl_qm60`, which is the event ID and match ID seperated by an underscore, match IDs are formated `qm[num]`, `sf[num]m[num]`, and `f[num]m[num]`. The first number always refers to a set between the same teams, so finals are usually `f1m[1-3]`. Semifinals usually end in `1`.\n"
                + "`&get_event [event_id]` - Gets event info, `[event_id]` is in the format `[year][state_or_province_abr][event_abr]`, e.g. Beach Blitch in 2023 was `2023cabl`\n"
                + "`&get_team_rank [team_number] [event_id]` - Plots info about a teams rank for an event, see above for argument format.\n"
                + "`&get_event_rankings [event_id]` - gets the rankings of all teams at an event. See above for argument format.\n"
                + "`&get_event_matches [event_id]` - Gets a summary of all matches played at the given event. See above for argument format.\n"
                + "`&get_team_event [team_number] [event_id]` - Gets a summary of all matches a team played during an event, and plots their score over time. See above for argument format.\n"
            )

            help1 = (
                "`&compare_teams_event [team_number] [team_number] [event_id]` - Compares two teams performance at an event. See above for argument format.\n"
                + "`&get_scouting_fields [event_id]` - Gets available fields for an event. NOTE: Requires a scouting sheet be set for the given event.\n"
                + "`&plot_scouting_field [event_id] [team_number] [field]` - Plots a numeric field from scouting data, you may have to wrap the `[field]` argument in quotes if it contains spaces. NOTE: Requires a scouting sheet be set for the given event.\n"
                + "`&match_breakdown [event_id] [match_number] [team_number]` - Gives a match breakdown from scouting data. `[match_number]` is the match number given in scouting forms, not from TBA. NOTE: Requires a scouting sheet be set for the given event."
                + "`&set_scouting_sheet [event_id] [sheet_id]` - *Requires Priviledged Role.* Sets the scouting sheet for the given event.\n"
                + "`&set_cache_expiration_time [time] [unit]` - *Requires Priviledged Role.* Sets the time till a cache item is considered expired.\n"
                + "`&get_cache_hit_rate` - Yeilds the rate at which cache items are used in favor of sending a new request to an API."
            )

            await ctx.send(help0)
            await ctx.send(help1)


    async def start(self):
        logging.log("BOT", "Starting Discord bot ...")
        await self.bot.start(self.token, reconnect=True)


    async def plot_line(self, ctx, data, x_label: str, y_label: str, ticks=None):            
        """
        Plots the given data and sends it in discord.
        """
        
        # Wait for plotting
        while self.plotting:
            sleep(0.25)

        # deny plotting to other async calls to this method
        logging.log("BOT", "Reserving PyPlot ...")
        self.plotting = True

        file_name = f"/tmp/blue1-{datetime.now().strftime('%M%I%S%f')}.png"
    
        pyplot.plot(range(1, len(data) + 1), data, linewidth=2, color='blue')
        pyplot.plot(range(1, len(data) + 1), data, 'o', color='blue')
        pyplot.xlabel(x_label)
        pyplot.ylabel(y_label)
        pyplot.xticks(range(1, len(data) + 1) if ticks is None else ticks)

        _, upper = pyplot.ylim()
        pyplot.ylim(0, upper)

        pyplot.savefig(file_name)
        pyplot.clf()

        # allow plotting by other async calls of this metho
        logging.log("BOT", "Releasing PyPlot ...")
        self.plotting = False

        await ctx.send("", file=discord.File(file_name))
        os.remove(file_name)


    def get_event_sheet(self, event: str) -> Optional[sheets.Spreadsheet]:
        """
        Get an event's scouting spreadsheet if it has been saved, otherwise 
        produce it from a sheet ID if it has been set. If both options fail this
        method returns `None`.
        """

        try:
            logging.log("BOT", f"Sheet for {event} already instantiated")
            return self.event_sheets[event]
        except:
            pass

        logging.log("BOT", f"Getting sheet for {event} ...")
        id = state.STATE.get(f"scouting_sheet_id_{event}")

        if id is None:
            logging.log("BOT", f"No sheet set for {event}")
            return None

        creds = sheets.produce_valid_credentials()
        service = sheets.get_sheets_service(creds)
        sheet = sheets.Spreadsheet(service, id)
        logging.log("BOT", f"Instantiated sheet for {event}, saving ...")
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

