# -*- coding: utf-8 -*-
import requests

from Database.Connection import post_chat, get_constant_message
from Database.SheetConnection import save_booking_to_sheet, add_user_to_sheet, get_chatbot_turn_on, \
    get_user_existed_on_sheet, get_follow_up_turn_on


class MessageClient:
    def __init__(self, page_access_token, page_id):
        self.page_access_token = page_access_token
        self.page_id = page_id
        self.api_url = 'https://graph.facebook.com/v21.0/me/messages'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.page_access_token}'
        }

    # Gửi tin nhắn trả lời qua Facebook Messenger
    def send_message(self, recipient_id, message_text, user_input_message):
        if isinstance(message_text, tuple):
            text_part, json_part = message_text
            message_text = text_part
            if json_part:
                message_text += "\n\n" + str(json_part)

        # Đảm bảo message_text là chuỗi
        if not isinstance(message_text, str):
            print(f"❌ Lỗi: message_text không phải là chuỗi: {type(message_text)}")
            message_text = "Em xin lỗi, hiện tại có lỗi xảy ra khi xử lý tin nhắn ạ 🙇"

        data = {
            'recipient': {'id': recipient_id},
            'message': {'text': message_text}
        }

        if not message_text.strip():
            print("❌ Tin nhắn rỗng, không gửi đi")
            return {"error": "Tin nhắn rỗng, không gửi đi"}
        else:
            try:
                response = requests.post(self.api_url, headers=self.headers, json=data)
                response.raise_for_status()
                result = response.json()
                print(f"✅ Đã gửi tin nhắn thành công: {result}")
                post_chat(recipient_id, [{"role": "user", "content": user_input_message},
                                         {"role": "assistant", "content": message_text}])
                return result
            except requests.exceptions.RequestException as e:
                print(f"❌ Gửi tin nhắn thất bại: {e}")
                return {"error": str(e)}

    def send_introduce_message(self, recipient_id):
        data = {
            'recipient': {'id': recipient_id},
            'message': {'text': get_constant_message("introduce")}
        }
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=data
        )
        return response.json()

    def send_booking_message(self, user_id, message_text=""):
        user_name = self.get_user_name_from_conversation_id(user_id)

        self.send_message_with_no_logs(recipient_id=user_id,
                                       message_text="Quý khách cho em xin Tên, Số điện thoại và Thời gian đến để em kiểm tra lịch cho mình ngay ạ!")
        save_booking_to_sheet(user_id=user_id, user_name=user_name, message_text=message_text)
        return

    # -*- coding: utf-8 -*-
    # Gửi tin nhắn hình ảnh phòng khám qua Messenger
    def send_image(self, recipient_id):
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
        response = requests.post(self.api_url, headers=self.headers, json=data)
        return response.json()

    def send_message_with_no_logs(self, recipient_id, message_text):
        data = {
            'recipient': {'id': recipient_id},
            'message': {
                'text': message_text
            },
            "tag": "CONFIRMED_EVENT_UPDATE"
        }
        response = requests.post(self.api_url, headers=self.headers, json=data)
        return response.json()

    def save_user(self, user_id, is_chatbot_on=False):
        """
        Lấy tên người dùng từ Facebook API.
        """
        user_name = self.get_user_name_from_conversation_id(user_id)
        add_user_to_sheet(user_id=user_id, user_name=user_name, is_chatbot_on=is_chatbot_on)

    @staticmethod
    def check_permission_auto_message(user_id):
        """
        Kiểm tra xem chatbot có đang bật cho người dùng này không.
        """
        try:
            return get_chatbot_turn_on(user_id) or not get_user_existed_on_sheet(user_id)
        except Exception as e:
            print(f"❌ Lỗi khi kiểm tra trạng thái chatbot: {e}")
            return False

    @staticmethod
    def check_permission_follow_up(user_id):
        """
        Kiểm tra xem follow up có đang bật cho người dùng này không.
        """
        try:
            return get_follow_up_turn_on(user_id)
        except Exception as e:
            print(f"❌ Lỗi khi kiểm tra trạng thái follow up: {e}")
            return False

    def get_conversation_id(self, user_id):
        """
        Lấy ID cuộc trò chuyện của người dùng từ sheet.
        """
        try:
            url = f'https://graph.facebook.com/v22.0/me/conversations'
            params = {
                'user_id': user_id,
                'platform': 'MESSENGER',
                'access_token': self.page_access_token
            }
            response = requests.get(url=url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('data')[0].get('id')
        except Exception as e:
            print(f"❌ Lỗi khi lấy ID cuộc trò chuyện: {e}")
            return None

    def get_user_name_from_conversation_id(self, user_id):
        try:
            conversation_id = self.get_conversation_id(user_id)
            if conversation_id is None:
                return "Người dùng"
            url = f"https://graph.facebook.com/v22.0/{conversation_id}"
            params = {
                'fields': 'messages,id,participants',
                'access_token': self.page_access_token
            }
            response = requests.get(url=url, params=params)
            if response.status_code == 200:
                data = response.json()
                participants = data.get('participants', {}).get('data', [])
                return next((item.get('name', 'Người dùng') for item in participants if item.get('id') != self.page_id), 'Người dùng')
            else:
                return "Người dùng"
        except Exception as e:
            print(f"❌ Lỗi khi lấy tên người dùng từ ID cuộc trò chuyện: {e}")
            return "Người dùng"
