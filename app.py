# -*- coding: utf-8 -*-
import re
import time

import openai
import requests
from flask import Flask, request

from Connection import get_credentials, get_functions, get_constant_message, get_faq, get_prompt, post_chat, get_chat

app = Flask(__name__)

# Example usage
try:
    VERIFY_TOKEN, PAGE_ACCESS_TOKEN, OPENAI_API_KEY = get_credentials()
    print("✅ Credentials retrieved successfully")
except Exception as e:
    print(f"❌ Error retrieving credentials: {e}")


# -*- coding: utf-8 -*-
# Gửi tin nhắn hình ảnh phòng khám qua Messenger
def send_image(recipient_id):
    params = {
        'access_token': PAGE_ACCESS_TOKEN
    }
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'recipient': {'id': recipient_id},
        'message': {
            'attachment': {
                "type": "image",
                "payload": {
                    "url": "https://i.imgur.com/I0IFANJ.png"
                }
            }
        }
    }
    response = requests.post(
        'https://graph.facebook.com/v21.0/me/messages',
        params=params,
        headers=headers,
        json=data
    )
    return response.json()


# Gửi tin nhắn trả lời qua Facebook Messenger
def send_message(recipient_id, message_text, user_input_message):
    if isinstance(message_text, tuple):
        text_part, json_part = message_text
        message_text = text_part
        if json_part:
            message_text += "\n\n" + str(json_part)

    # Đảm bảo message_text là chuỗi
    if not isinstance(message_text, str):
        print(f"❌ Lỗi: message_text không phải là chuỗi: {type(message_text)}")
        message_text = "Em xin lỗi, hiện tại có lỗi xảy ra khi xử lý tin nhắn ạ 🙇"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + PAGE_ACCESS_TOKEN
    }
    data = {
        'recipient': {'id': recipient_id},
        'message': {'text': message_text}
    }

    if not message_text.strip():
        print("❌ Tin nhắn rỗng, không gửi đi")
        return {"error": "Tin nhắn rỗng, không gửi đi"}
    else:
        try:
            response = requests.post(
                'https://graph.facebook.com/v21.0/me/messages',
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            print(f"✅ Đã gửi tin nhắn thành công: {result}")
            post_chat(recipient_id, [{"role": "user", "content": user_input_message},
                                     {"role": "assistant", "content": message_text}])
            return result
        except requests.exceptions.RequestException as e:
            print(f"❌ Gửi tin nhắn thất bại: {e}")
            return {"error": str(e)}


def send_introduce_message(recipient_id):
    params = {
        'access_token': PAGE_ACCESS_TOKEN
    }
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'recipient': {'id': recipient_id},
        'message': {'text': get_constant_message("introduce")}
    }
    response = requests.post(
        'https://graph.facebook.com/v21.0/me/messages',
        params=params,
        headers=headers,
        json=data
    )
    return response.json()


# Gửi tin nhắn đến ChatGPT
def ask_chatgpt(message, sender_id):
    openai.api_key = OPENAI_API_KEY

    # Prepare data
    functions = get_functions()
    faq_data = filter_faq_data(get_faq())
    chat_history = get_chat(user_id=sender_id)  # should return list of messages or None

    # System prompt with FAQ
    system_message = {
        "role": "system",
        "content": get_prompt() +
                   "Các thông tin FAQ có sẵn là:\n" +
                   '\n'.join([f"{k}: {v}" for k, v in faq_data.items()])
    }

    # Build messages list
    messages = [system_message]
    if chat_history:
        messages.extend(chat_history)
    messages.append({"role": "user", "content": message})

    # Send to OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",  # Đổi từ gpt-3.5-turbo-1106
        functions=functions,
        function_call="auto",
        messages=messages,
        temperature=0.7,
        # max_tokens=150,
    )

    return response['choices'][0]['message']


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
        handle_entry(entry)

    return "EVENT_RECEIVED", 200


def handle_entry(entry):
    messaging_events = entry.get('messaging', [])
    for event in messaging_events:
        handle_message_event(event)


def handle_message_event(event):
    sender_id = event['sender']['id']
    recipient_id = event['recipient']['id']
    message_text = event.get('message', {}).get('text')

    if sender_id == recipient_id:
        print(f"📩 Ignoring message from self: {sender_id}")
        return

    print(f"📩 Message from {sender_id}: {message_text}")

    if message_text:
        try:
            response = ask_chatgpt(message_text, sender_id)

            if response.get("function_call"):
                send_introduce_message(sender_id)
                time.sleep(2)
                send_image(sender_id)

            content = response.get("content", "")
            text_part, json_part = split_text_and_json(content)
            send_message(sender_id, (text_part, json_part), message_text)

        except Exception as e:
            print(f"❌ Error processing message: {e}")


def split_text_and_json(response_text):
    """
    Tách phần text và JSON từ phản hồi của GPT.
    """
    if not isinstance(response_text, str):
        print(f"[⚠️] Invalid response_text type: {type(response_text)}")
        return "", None

    pattern = r"```json\s*(\{[\s\S]*?\})\s*```"
    match = re.search(pattern, response_text)

    if match:
        json_part = match.group(1).strip()
        text_without_json = re.sub(pattern, '', response_text, flags=re.DOTALL).strip()
        return text_without_json, json_part

    return response_text.strip(), None


def filter_faq_data(data) -> dict:
    """
    Lọc dữ liệu FAQ để chỉ lấy các câu hỏi và câu trả lời.
    """
    faq_data = {}
    for item in data:
        question = item.get('question')
        answer = item.get('answer')

        if not question or not answer:
            continue

        if isinstance(answer, dict):
            combined = '\n'.join([f"- {k}: {v}" for k, v in answer.items()])
            faq_data[question] = combined
        elif isinstance(answer, list):
            faq_data[question] = combine_list_dict(answer)

        else:
            faq_data[question] = answer

    return faq_data


def combine_list_dict(data):
    """
    Combine values of a specific key from a list of dictionaries.
    """
    combined_values = []
    for item in data:
        if isinstance(item, list):
            for sub_item in item:
                if isinstance(sub_item, dict):
                    combined_values.append(', '.join([f"{k}: {v}" for k, v in sub_item.items()]))
        elif isinstance(item, dict):
            combined_values.append(', '.join([f"{k}: {v}" for k, v in item.items()]))

    return combined_values


if __name__ == '__main__':
    app.run(port=5000, debug=True, use_reloader=False)

app.config['APPLICATION_ROOT'] = '/chatbot'
