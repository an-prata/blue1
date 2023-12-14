# Copyright (c) Evan Overman 2023 (https://an-prata.it/)
# Licensed under the MIT License
# See LICENSE file at repository root for details.

import os.path
from enum import StrEnum
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from . import logging

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDENTIALS_PATH = 'credentials.json'
TOKEN_PATH = 'token.json'

sheet_max_column = 26
sheet_max_row = 100

SHEET_BOUNDS_X_CELL = 'A1'
SHEET_BOUNDS_Y_CELL = 'B1'
SHEET_BOUNDS_RANGE = f"{SHEET_BOUNDS_X_CELL}:{SHEET_BOUNDS_Y_CELL}"
DEFAULT_SHEET_NAME = 'Sheet1'

active_sheets: dict = {}

class ValueInputOption(StrEnum):
    RAW = 'RAW'
    USER_ENTERED = 'USER_ENTERED'


class Spreadsheet:
    id: str
    service: Resource


    def __init__(self, service: Resource, id: str):
        self.service = service
        self.id = id
    

    def create_sheet(self, 
                     sheet_name: str, 
                     colums: int, 
                     rows: int, 
                     color_r: float=0.0, 
                     color_g: float=0.2,
                     color_b: float=1.0
                     ):
        """
        Creates a new sheet with the given name, dimensions, and tab color.

        This method may throw an exception on faulty parameters or failure to
        use the Google Sheets API.
        """
        
        body = { 
            'requests': [
                {
                    'addSheet': {
                        'properties': {
                            'title': sheet_name,
                            'gridProperties': {
                                'rowCount': rows,
                                'columnCount': colums
                            },
                            'tabColor': {
                                'red': color_r,
                                'green': color_g,
                                'blue': color_b
                            }
                        }
                    }
                }
            ]
        }

        (
            self
            .service
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=self.id, 
                body=body
            )
            .execute()
        )


    def write_cells(self, cell_range: str, values: [[str]], input_option: ValueInputOption):
        """
        Writes values to the given cell range. The `values` list should contain
        elemnts of type `[str]`. Each element of `values` will represent a row
        of values. `cell_range` is given in the format 
        `[sheet]![column][row]:[column][row]`.

        This method may throw an exception on faulty parameters or failure to
        use the Google Sheets API.
        """

        body = { 'values': values }

        (
            self
            .service
            .spreadsheets()
            .values()
            .update(
                spreadsheetId=self.id,
                range=cell_range,
                valueInputOption=input_option,
                body=body
            )
            .execute()
        )


    def get_cells(self, cell_range: str):
        """
        Gets values in the given range and returns a list in which each element
        represent a row of values. `cell_range` is given in the format 
        `[sheet]![column][row]:[column][row]`.

        This method may throw an exception on faulty parameters or failure to
        use the Google Sheets API.
        """

        return (
            self
            .service
            .spreadsheets()
            .values()
            .get(
                spreadsheetId=self.id,
                range=cell_range
            )
            .execute()
        )['values']


    def get_sheet_bounds(self, sheet_name: str = DEFAULT_SHEET_NAME) -> (int, int):
        """
        Get a (rows, columns) two-tuple for the bounds of a spread sheet. This 
        function assumes that the spreadsheet's data begins at the cell `A1`, and
        that at least the cells in column `A` and in row `1` are populated 
        entirely.

        This method may throw an exception on faulty parameters or failure to
        use the Google Sheets API.
        """

        global sheet_max_column
        global sheet_max_row

        origin = f"{sheet_name}!A1"
        right_bound = f"{sheet_name}!{column_num_to_alpha(sheet_max_column)}1"
        lower_bound = f"{sheet_name}!A{sheet_max_row}"
        countersheet = get_blue1_countersheet(sheet_name)

        try:
            self.create_sheet(countersheet, 2, 1)
        except HttpError:
            # We are going to assume this exception is due to the sheet already
            # existing, which is fine.
            pass
        
        values = [
            [ 
                f"=COUNTA({origin}:{lower_bound})",
                f"=COUNTA({origin}:{right_bound})"
            ]
        ]

        self.write_cells(
            f"{countersheet}!{SHEET_BOUNDS_RANGE}",
            values,
            ValueInputOption.USER_ENTERED
        )

        data = self.get_cells(f"{countersheet}!{SHEET_BOUNDS_RANGE}")

        if int(data[0][0]) == sheet_max_row:
            sheet_max_row *= 2
            return self.get_sheet_bounds(sheet_name)

        if int(data[0][1]) == sheet_max_column:
            sheet_max_column *= 2
            return self.get_sheet_bounds(sheet_name)
        
        return (int(data[0][0]), int(data[0][1]))


    def get_fields(self, sheet_bounds: (int, int), sheet_name: str = DEFAULT_SHEET_NAME) -> [str]:
        """
        Gets the fields associated with this spreadsheet. This method assumes
        that the sheet is set up so that the first row has field names for the 
        rows below.
        
        This method may throw an exception on faulty parameters or failure to
        use the Google Sheets API.
        """

        _, columns = sheet_bounds
        columns = int(columns)
        fields = self.get_cells(f"{sheet_name}!A1:{column_num_to_alpha(columns)}1")[0]
        return fields

    
    def get_row_dict(self, 
                     row: int, 
                     sheet_bounds: (int, int), 
                     sheet_name: str = DEFAULT_SHEET_NAME
                     ) -> dict:
        """
        Gets a row of the sheet using the top row as keys to the values from the
        given row. This method assums that the sheet is set up with the top row
        being labels of the data in each column.

        This method may throw an exception on faulty parameters or failure to
        use the Google Sheets API.
        """
        
        rows, columns = sheet_bounds

        rows = int(rows)
        columns = int(columns)

        keys = self.get_cells(f"{sheet_name}!A1:{column_num_to_alpha(columns)}1")[0]
        values = self.get_cells(f"{sheet_name}!A{row}:{column_num_to_alpha(columns)}{row}")[0]

        return dict(zip(keys, values))


    def get_column_list(self, 
                        column: str, 
                        sheet_bounds: (int, int), 
                        sheet_name: str = DEFAULT_SHEET_NAME
                        ) -> [str]:
        """
        Returns a list of all values in the given column on the given sheet.
        This method assumes that the first row is for labels of each column and
        thus yeilds a list of values in the given column starting at the second
        row.

        This method may throw an exception on faulty parameters or failure to
        use the Google Sheets API.
        """

        rows, columns = sheet_bounds

        rows = int(rows)
        columns = int(columns)

        values = self.get_cells(f"{sheet_name}!{column}2:{column}{rows}")
        return [x[0] for x in values]


def get_blue1_countersheet(sheet_name: str) -> str:
    return f"(Blue1) {sheet_name}"


def column_num_to_alpha(num: int) -> str:
    """
    Converts a column number to a string representing that column.
    """
    
    if num < 1:
        logging.log("SHEETS", "Columns are considered 1 indexed, not zero")
    
    A = 65

    num -= 1
    last = num % 26

    if last == num:
        return f"{chr(A + last)}"
    
    leading = int((num - last) / 26)
    return f"{chr(A + leading)}{chr(A + last)}"


def produce_valid_credentials() -> Credentials:
    """
    Produces valid credentials from a token file at `TOKEN_PATH` if it is 
    available and valid. In the case it is not this function will move to use a
    crednetials file at `CREDENTIALS_PATH` and will produce a token file at
    `TOKEN_PATH` automatically.
    """

    credentials: Credentials = None

    logging.log("SHEETS", f"Producing credentials ...")

    if os.path.exists(TOKEN_PATH):
        logging.log("SHEETS", f"Using {TOKEN_PATH} for credentials")
        credentials = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            #logging.log("SHEETS", "Credentials expired, refreshing token ...")
            #credentials.refresh(Request())
            #logging.log("SHEETS", "Refreshed token")

            # Above is the official way to refresh creds, but for whatever 
            # reason it doesn't work, at least not on my laptop, so for now we 
            # will default producing new credentials.

            logging.log("SHEETS", f"Using client {CREDENTIALS_PATH} to produce credentials ...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            credentials = flow.run_local_server(port=0)

        else:
            logging.log("SHEETS", f"Using client {CREDENTIALS_PATH} to produce credentials ...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            credentials = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as token_file:
            logging.log("SHEETS", f"Saving new credentials to {TOKEN_PATH}")
            token_file.write(credentials.to_json())

    return credentials


def get_sheets_service(credentials: Credentials) -> Resource:
    """
    Gets a `Resource` for interacting with google sheets with the given valie
    credentials.
    """

    return build('sheets', 'v4', credentials=credentials)

