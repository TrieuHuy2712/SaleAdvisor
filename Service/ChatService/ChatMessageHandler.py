# -*- coding: utf-8 -*-
import re
import time
from dataclasses import dataclass

from Database.Connection import post_chat
from Database.SheetConnection import get_user_existed_on_sheet, add_user_permission_user_to_sheet
from Service.ChatService import IChatService
from Service.MessageService import MessageClient

processed_message_ids = set()
@dataclass
class ChatMessageHandler:
    chat_service: IChatService
    messenger: MessageClient
    fb_page_id: str

    def handle_entry(self, entry):
        messaging_events = entry.get('messaging', [])
        for event in messaging_events:
            self.handle_message_event(event)

    def handle_message_event(self, event):
        message = event.get('message')
        message_id = message.get('mid')
        if not message_id:
            return

        if message_id in processed_message_ids:
            print(f"⚠️ Đã xử lý message_id: {message_id}, bỏ qua.")
            return

        processed_message_ids.add(message_id)

        sender_id = event['sender']['id']
        recipient_id = event['recipient']['id']
        message_text = event.get('message', {}).get('text')

        if sender_id == recipient_id:
            print(f"📩 Ignoring message from self: {sender_id}")
            return

        print(f"📩 Message from {sender_id}: {message_text}")

        "Check chat bot is active "
        if not get_user_existed_on_sheet(sender_id) and sender_id != self.fb_page_id:
            self.messenger.save_user(sender_id, True)

        if (message_text
            and self.messenger.check_permission_auto_message(sender_id)) \
                and sender_id != self.fb_page_id:
            try:
                response = self.chat_service.ask(message_text, sender_id)

                if response.get("function_call"):
                    self.messenger.send_introduce_message(sender_id)
                    time.sleep(2)
                    self.messenger.send_image(sender_id)

                content = response.get("content", "")
                content = self.chat_service.convert_markdown_bold_to_unicode(content)
                text_part, json_part = self.split_text_and_json(content)

                if text_part == "booking":
                    self.messenger.send_booking_message(sender_id, message_text=message_text)
                    return
                self.messenger.send_message(sender_id, (text_part, json_part), message_text)

            except Exception as e:
                print(f"❌ Error processing message: {e}")
        elif (message_text
              and not self.messenger.check_permission_auto_message(sender_id)
              and sender_id != self.fb_page_id):  # Case when chatbot turned off and user sends a message
            post_chat(sender_id, [{"role": "user", "content": message_text}])
        elif (message_text  # Case when chatbot turned off and page sends a message
              and sender_id == self.fb_page_id
              and not self.messenger.check_permission_auto_message(recipient_id)):
            post_chat(recipient_id, [{"role": "assistant", "content": message_text}], is_update=False)


    @staticmethod
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
