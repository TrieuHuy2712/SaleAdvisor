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

    if not all([verify_token, page_access_token, openai_api_key]):
        raise ValueError("Missing required credentials in the database")

    return verify_token, page_access_token, openai_api_key


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
    prompt = collection.find_one({}, {"_id": 0})

    if not prompt:
        raise ValueError("Prompt not found in the database")

    return prompt.get("content", "")


def post_chat(user_id, message):
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[CHAT_COLLECTION_NAME]

    # Query the collection for the post chat message
    existed_user = collection.find_one({"user_id": user_id})
    if existed_user:
        # Update existing user chat
        collection.update_one({"user_id": user_id}, {
            "$push": {
                "messages": {
                    "$each": message,
                    "$slice": -20
                }
            },  # 👈 Append thêm dòng mới
            "$set": {"updated_at": datetime.utcnow()},
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
                              upsert=True
                              )
    else:
        # Create new user chat
        collection.insert_one({"user_id": user_id, "messages": message,
                               "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()})


def get_chat(user_id):
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
