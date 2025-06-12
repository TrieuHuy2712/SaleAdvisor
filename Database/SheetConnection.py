import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json")
SHEET_KEY = "1GpYoPoG8TxLdXRs0TlzeC_P8d8w_0UWMSavJ5a0SNLI"


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
        sheet.append_row([user_id, user_name, True])
    except Exception as e:
        print(f"❌ Error adding user to sheet: {e}")


def get_chatbot_turn_on(user_id):
    """
    Check if the chatbot is turned on for a specific user.
    """
    try:
        sheet = get_google_sheet("Customer")
        all_values = sheet.get_all_records()
        matching_rows = [row for row in all_values if str(row.get('ID_Facebook')) == user_id]
        if matching_rows:
            return matching_rows[0].get('Turn on Chat bot', True)
        return False
    except Exception as e:
        print(f"❌ Error checking chatbot status: {e}")
        return False
