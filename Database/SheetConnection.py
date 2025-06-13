import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

from gspread_formatting import Color, format_cell_range, CellFormat

from Database.Connection import get_gg_sheet_key

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json")
SHEET_KEY = get_gg_sheet_key()


def get_google_sheet(sheet_name):
    """
    Connect to a specific Google Sheet by name.
    """
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_KEY).worksheet(sheet_name)
        return sheet
    except Exception as e:
        print(f"❌ Error connecting to Google Sheet: {e}")
        raise


def save_booking_to_sheet(user_id, user_name, message_text):
    """
    Save booking information to the 'Booking' sheet.
    """
    try:
        sheet = get_google_sheet("Booking")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, user_id, user_name, message_text])

        # Xác định dòng vừa thêm
        new_row_index = len(sheet.get_all_values())

        # Định dạng màu cho hàng đó (ví dụ màu nền vàng nhạt)
        yellow_fill = CellFormat(backgroundColor=Color(1, 1, 0.6))  # RGB (255, 255, 153))
        format_cell_range(sheet, f"A{new_row_index}:D{new_row_index}", yellow_fill)
        set_user_chatbot_action(user_id, False)  # Disable chatbot action after booking
    except Exception as e:
        print(f"❌ Error saving booking to sheet: {e}")


def get_user_existed_on_sheet(user_id):
    """
    Check if a user exists in the 'Customer' sheet by user_id.
    """
    try:
        sheet = get_google_sheet("Customer")
        all_values = sheet.get_all_records()
        matching_rows = [row for row in all_values if str(row.get('ID_Facebook')) == user_id]
        return len(matching_rows) > 0
    except Exception as e:
        print(f"❌ Error checking user existence on sheet: {e}")
        return False


def add_user_to_sheet(user_id, user_name):
    """
    Add a new user to the 'Customer' sheet.
    """
    try:
        sheet = get_google_sheet("Customer")
        if get_user_existed_on_sheet(user_id):
            print(f"User {user_id} already exists in the sheet.")
            return
        sheet.append_row([user_id, user_name, True, True])
    except Exception as e:
        print(f"❌ Error adding user to sheet: {e}")


def set_user_chatbot_action(user_id, action):
    """
    Set the chatbot action for a specific user in the 'Customer' sheet.
    """
    try:
        sheet = get_google_sheet("Customer")
        all_values = sheet.get_all_records()
        matching_rows = [row for row in all_values if str(row.get('ID_Facebook')) == user_id]
        if matching_rows:
            for row in matching_rows:
                row_index = all_values.index(row) + 2  # +2 because gspread is 1-indexed and has header row
                sheet.update_cell(row_index, 3, action)

        else:
            print(f"User {user_id} not found in the sheet.")
    except Exception as e:
        print(f"❌ Error setting user chatbot action: {e}")


def set_user_follow_up_action(user_id, action: bool):
    """
    Set the chatbot action for a specific user in the 'Customer' sheet.
    """
    try:
        sheet = get_google_sheet("Customer")
        all_values = sheet.get_all_records()
        matching_rows = [row for row in all_values if str(row.get('ID_Facebook')) == user_id]
        if matching_rows:
            for row in matching_rows:
                row_index = all_values.index(row) + 2  # +2 because gspread is 1-indexed and has header row
                sheet.update_cell(row_index, 4, action)

        else:
            print(f"User {user_id} not found in the sheet.")
    except Exception as e:
        print(f"❌ Error setting user chatbot action: {e}")


def get_chatbot_turn_on(user_id):
    """
    Check if the chatbot is turned on for a specific user.
    """
    try:
        sheet = get_google_sheet("Customer")
        all_values = sheet.get_all_records()
        matching_rows = [row for row in all_values if str(row.get('ID_Facebook')) == user_id]
        if matching_rows:
            return matching_rows[0].get('Turn on Chat bot', 'FALSE') == 'TRUE'
        return False
    except Exception as e:
        print(f"❌ Error checking chatbot status: {e}")
        return False


def get_follow_up_turn_on(user_id):
    """
    Check if follow-up is turned on for a specific user.
    """
    try:
        sheet = get_google_sheet("Customer")
        all_values = sheet.get_all_records()
        matching_rows = [row for row in all_values if str(row.get('ID_Facebook')) == user_id]
        if matching_rows:
            return matching_rows[0].get('Follow up', 'FALSE') == 'TRUE'
        return False
    except Exception as e:
        print(f"❌ Error checking follow-up status: {e}")
        return False
