# -*- coding: utf-8 -*-
import requests

from Database.Connection import post_chat, get_constant_message
from Database.SheetConnection import save_booking_to_sheet, add_user_to_sheet, get_chatbot_turn_on, \
    get_user_existed_on_sheet, get_follow_up_turn_on


class MessageClient:
    def __init__(self, page_access_token):
        self.page_access_token = page_access_token
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
        url = f"https://graph.facebook.com/v21.0/{user_id}"
        params = {
            'fields': 'first_name,last_name',
        }
        response = requests.get(url=url, headers=self.headers, params=params)
        data = response.json()

        if response.status_code != 200:
            self.send_message_with_no_logs(recipient_id=user_id,
                                           message_text="Cảm ơn quý khách đã liên hệ đặt lịch hẹn với phòng khám của chúng tôi. "
                                                        "Chúng tôi sẽ liên hệ lại với bạn trong thời gian sớm nhất để xác nhận lịch hẹn.")
            save_booking_to_sheet(user_id=user_id, user_name=f"Nguoi dung", message_text=message_text)
        else:
            first_name = data.get('first_name', 'Người dùng')
            last_name = data.get('last_name', '')
            self.send_message_with_no_logs(recipient_id=user_id,
                                           message_text="Cảm ơn quý khách đã liên hệ đặt lịch hẹn với phòng khám của chúng tôi. "
                                                        "Chúng tôi sẽ liên hệ lại với bạn trong thời gian sớm nhất để xác nhận lịch hẹn.")
            save_booking_to_sheet(user_id=user_id, user_name=f"{first_name} {last_name}", message_text=message_text)
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
        url = f"https://graph.facebook.com/v21.0/{user_id}"
        params = {
            'fields': 'first_name,last_name',
            'access_token': self.page_access_token
        }
        response = requests.get(url=url, params=params)
        if response.status_code == 200:
            data = response.json()
            username = f"{data.get('first_name', '')} {data.get('last_name', '')}"
            add_user_to_sheet(user_id=user_id, user_name=username, is_chatbot_on=is_chatbot_on)
        else:
            add_user_to_sheet(user_id=user_id, user_name="Người dùng", is_chatbot_on=is_chatbot_on)
            # print(f"❌ Lỗi khi lấy tên người dùng: {response.text}")
            # return "Người dùng"

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
