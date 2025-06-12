# -*- coding: utf-8 -*-
import re
import time
from dataclasses import dataclass

from Database.SheetConnection import get_user_existed_on_sheet
from Service.ChatService import IChatService
from Service.MessageService import MessageClient


@dataclass
class ChatMessageHandler:
    chat_service: IChatService
    messenger: MessageClient

    def handle_entry(self, entry):
        messaging_events = entry.get('messaging', [])
        for event in messaging_events:
            self.handle_message_event(event)

    def handle_message_event(self, event):
        sender_id = event['sender']['id']
        recipient_id = event['recipient']['id']
        message_text = event.get('message', {}).get('text')

        if sender_id == recipient_id:
            print(f"📩 Ignoring message from self: {sender_id}")
            return

        print(f"📩 Message from {sender_id}: {message_text}")

        "Check chat bot is active "
        if not get_user_existed_on_sheet(sender_id):
            self.messenger.save_user(sender_id)
            return

        if message_text and self.messenger.check_permission_auto_message(sender_id):
            try:
                response = self.chat_service.ask(message_text, sender_id)

                if response.get("function_call"):
                    self.messenger.send_introduce_message(sender_id)
                    time.sleep(2)
                    self.messenger.send_image(sender_id)

                content = response.get("content", "")
                text_part, json_part = self.split_text_and_json(content)

                if text_part == "booking":
                    self.messenger.send_booking_message(sender_id, message_text=message_text)
                    return
                self.messenger.send_message(sender_id, (text_part, json_part), message_text)

            except Exception as e:
                print(f"❌ Error processing message: {e}")

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
