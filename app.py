# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify

from Database.Connection import get_credentials
from Service.ChatService.ChatMessageHandler import ChatMessageHandler
from Service.ChatService.OpenAIChatService import OpenAIChatService
from Service.MessageService.MessageClient import MessageClient
from Service.TaskScheduler import TaskScheduler

app = Flask(__name__)

try:
    VERIFY_TOKEN, PAGE_ACCESS_TOKEN, OPENAI_API_KEY, GPT_MODEL, RECURRING_TIME, FB_PAGE_ID = get_credentials()
    messenger = MessageClient(PAGE_ACCESS_TOKEN)
    chat_service = OpenAIChatService(openai_key=OPENAI_API_KEY, model=GPT_MODEL)
    chatgpt_bridge = ChatMessageHandler(chat_service=chat_service, messenger=messenger, fb_page_id=FB_PAGE_ID)
    task_scheduler = TaskScheduler(chatService=chatgpt_bridge.chat_service, message=messenger,
                                   recurring_time=RECURRING_TIME)
    print("✅ Credentials retrieved successfully")
except Exception as e:
    print(f"❌ Error retrieving credentials: {e}")


@app.route('/webhook', methods=['GET'])
def verify():
    # Facebook webhook verification
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified ✅")
        return challenge, 200
    else:
        return "Verification failed", 403


@app.route('/webhook', methods=['POST'])
def webhook():
    print("📨 Received a POST request to /webhook")
    data = request.get_json()

    if data.get('object') != 'page':
        return "Not a page object", 404

    for entry in data.get('entry', []):
        chatgpt_bridge.handle_entry(entry)

    return "EVENT_RECEIVED", 200


@app.route('/api/delete_cache_permission/<user_id>', methods=['DELETE'])
def delete_cache_permission_api(user_id):
    """
    API endpoint to delete cached permission for a user.
    """
    try:
        if user_id in chatgpt_bridge.permission_cache:
            ChatMessageHandler.delete_cache_permission(user_id)
            return jsonify({"message": f"Permission cache for user {user_id} has been deleted."}), 200
        else:
            return jsonify({"error": f"No cached permission found for user {user_id}."}), 404
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True, use_reloader=False)

app.config['APPLICATION_ROOT'] = '/chatbot'
