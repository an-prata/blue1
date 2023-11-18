# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

from . import tba
import json

if __name__ == '__main__':
    t = tba.tba_from_env()
    json_dict = t.get_team_matches_json(7042, year=2023)
    print(json.dumps(json_dict, indent=4))

