# -*- coding: utf-8 -*-
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection URI
MONGO_URI = "mongodb://localhost:27017"  # Replace with your MongoDB URI
DATABASE_NAME = "saleadvisor"
CONFIG_COLLECTION_NAME = "config"
FUNCTION_COLLECTION_NAME = "functions"
CONSTANT_MESSAGE_COLLECTION_NAME = "constant_message"
FAQ_COLLECTION_NAME = "faq"
PROMPT_COLLECTION_NAME = "prompt"
CHAT_COLLECTION_NAME = "chat"


def get_credentials():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[CONFIG_COLLECTION_NAME]

    # Query the collection for credentials
    credentials = collection.find_one()  # Adjust the query as needed

    if not credentials:
        raise ValueError("Credentials not found in the database")

    # Extract the required keys
    verify_token = credentials.get("verify_token")
    page_access_token = credentials.get("page_access_token")
    openai_api_key = credentials.get("openai_api_key")
    gpt_model = credentials.get("gpt_model", "gpt-3.5-turbo-1106")
    recurring_time = credentials.get("recurring_time", 60)
    fb_page_id = credentials.get("fb_page_id")

    if not all([verify_token, page_access_token, openai_api_key, gpt_model]):
        raise ValueError("Missing required credentials in the database")

    return verify_token, page_access_token, openai_api_key, gpt_model, recurring_time, fb_page_id


def get_functions():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[FUNCTION_COLLECTION_NAME]

    # Query the collection for the prompt
    function = list(collection.find({}, {"_id": 0}))

    if not function:
        raise ValueError("Function not found in the database")

    return function


def get_constant_message(type: str):
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[CONSTANT_MESSAGE_COLLECTION_NAME]

    # Query the collection for the constant message
    constant_message = collection.find_one({"type": type})

    if not constant_message:
        raise ValueError("Constant message not found in the database")

    return constant_message.get("content", "")


def get_faq():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[FAQ_COLLECTION_NAME]

    # Query the collection for FAQs
    faq = list(collection.find({}, {"_id": 0}))

    if not faq:
        raise ValueError("FAQ not found in the database")

    return faq


def get_prompt():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[PROMPT_COLLECTION_NAME]

    # Query the collection for the prompt
    prompt = collection.find_one({"promptType": "main"}, {"_id": 0})

    if not prompt:
        raise ValueError("Prompt not found in the database")

    return prompt.get("content", "")


def get_follow_up_prompt():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[PROMPT_COLLECTION_NAME]

    # Query the collection for the follow-up prompt
    prompt = collection.find_one({"promptType": "follow-up"}, {"_id": 0})

    if not prompt:
        raise ValueError("Follow-up prompt not found in the database")

    return prompt.get("content", "")


def get_welcome_prompt():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[PROMPT_COLLECTION_NAME]

    # Query the collection for the introduce prompt
    prompt = collection.find_one({"promptType": "welcome"}, {"_id": 0})

    if not prompt:
        raise ValueError("Welcome prompt not found in the database")

    return prompt.get("content", "")


def get_classify_prompt():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[PROMPT_COLLECTION_NAME]

    # Query the collection for the classify prompt
    prompt = collection.find_one({"promptType": "classify"}, {"_id": 0})

    if not prompt:
        raise ValueError("Classify prompt not found in the database")

    return prompt.get("content", "")


def post_chat(user_id, message, is_update=True):
    """
    Posts or updates chat messages for a user in the MongoDB collection.

    Args:
        user_id (str): The ID of the user.
        message (list): The list of messages to be added.
        is_update (bool): Flag to determine whether to update the `updated_at` field. Defaults to True.
    """
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[CHAT_COLLECTION_NAME]

    # Query the collection for the user
    existed_user = collection.find_one({"user_id": user_id})

    update_data = {
        "$push": {
            "messages": {
                "$each": message,
                "$slice": -20
            }
        },
        "$setOnInsert": {"created_at": datetime.utcnow()}
    }

    if is_update:
        update_data["$set"] = {"updated_at": datetime.utcnow()}

    if existed_user:
        # Update existing user chat
        collection.update_one({"user_id": user_id}, update_data, upsert=True)
    else:
        # Create new user chat
        collection.insert_one({
            "user_id": user_id,
            "messages": message,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })


def get_chat_by_userid(user_id):
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[CHAT_COLLECTION_NAME]

    # Query the collection for the chat messages
    chat = collection.find_one({"user_id": user_id}, {"_id": 0})

    if not chat:
        return None

    messages = chat.get("messages", [])

    # ✅ Get 20 last messages
    last_messages = messages[-20:] if len(messages) > 10 else messages

    return last_messages


def get_all_chat():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[CHAT_COLLECTION_NAME]

    # Query the collection for all chat messages
    chats = list(collection.find({}, {"_id": 0}))

    if not chats:
        return []

    return chats


def get_gg_sheet_key():
    """
    Get the Google Sheet key from the database.
    """
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[CONFIG_COLLECTION_NAME]

    sheet_key = collection.find_one()

    if not sheet_key:
        raise ValueError("Sheet key not found in the database")

    return sheet_key.get("sheet_key", "")
