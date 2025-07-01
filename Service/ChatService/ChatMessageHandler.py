# -*- coding: utf-8 -*-
import re
import time
import threading
from collections import defaultdict
from dataclasses import dataclass

from Database.Connection import post_chat, get_chat_by_userid, get_follow_up_keywords
from Database.SheetConnection import get_user_existed_on_sheet
from Service.ChatService import IChatService
from Service.MessageService import MessageClient

processed_message_ids = set()
# TTL cache: auto-expire message_id after 5 minutes
processed_message_ids = TTLCache(maxsize=10000, ttl=300)
message_buffers = defaultdict(list)
debounce_timers = {}
DEBOUNCE_DELAY_SECONDS = 10


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

                if json_part:
                    self.messenger.send_message(sender_id, (text_part, json_part), message_text)
                    return
                else:  # Case when no JSON part and Split multiple message
                    main, followup = self.split_main_and_followup(text_part, sender_id)

                    # User Chat
                    post_chat(sender_id, [{"role": "user", "content": message_text}], is_update=True)

                    # Main Chat
                    self.messenger.send_message_with_no_logs(sender_id, main)
                    post_chat(sender_id, [{"role": "assistant", "content": main}], is_update=False)

                    # Follow-up Chat
                    if followup or followup != "\n\n":
                        time.sleep(3)  # Delay to avoid rate limiting
                        self.messenger.send_message_with_no_logs(sender_id, followup)
                        post_chat(sender_id, [{"role": "assistant", "content": followup}], is_update=False)

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

    def debounce_user_message(self, sender_id, message_text):
        message_buffers[sender_id].append(message_text)

        if sender_id in debounce_timers:
            debounce_timers[sender_id].cancel()

        timer = threading.Timer(
            DEBOUNCE_DELAY_SECONDS,
            self.debounce_process_message,
            args=(sender_id,)
        )
        debounce_timers[sender_id] = timer
        timer.start()

    def debounce_process_message(self, sender_id):
        # ✅ Loại trùng nội dung giữ thứ tự
        message_texts = list(dict.fromkeys(message_buffers[sender_id]))
        full_message = "\n".join(message_texts)
        message_buffers[sender_id].clear()

        try:
            response = self.chat_service.ask(full_message, sender_id)

            if response.get("function_call"):
                self.messenger.send_introduce_message(sender_id)
                time.sleep(2)
                self.messenger.send_image(sender_id)

            content = response.get("content", "")
            content = self.chat_service.convert_markdown_bold_to_unicode(content)
            text_part, json_part = self.split_text_and_json(content)

            if text_part == "booking":
                self.messenger.send_booking_message(sender_id, message_text=full_message)
                return

            if json_part:
                self.messenger.send_message(sender_id, (text_part, json_part), full_message)
                return
            else:
                main, followup = self.split_main_and_followup(text_part, sender_id)

                post_chat(sender_id, [{"role": "user", "content": full_message}], is_update=True)

                self.messenger.send_message_with_no_logs(sender_id, main)
                post_chat(sender_id, [{"role": "assistant", "content": main}], is_update=False)

                if followup or followup != "\n\n":
                    time.sleep(3)
                    self.messenger.send_message_with_no_logs(sender_id, followup)
                    post_chat(sender_id, [{"role": "assistant", "content": followup}], is_update=False)

        except Exception as e:
            print(f"❌ Error during debounce processing for user {sender_id}: {e}")

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

    def split_main_and_followup(self, text: str, user_id: str) -> tuple:
        """
        Splits the input text into main reply and follow-up sections based on keywords.
        """
        blocks = text.strip().split("\n\n")
        chat_history = get_chat_by_userid(user_id=user_id)
        follow_up_keywords = get_follow_up_keywords()

        # Separate blocks into main reply and follow-up
        main_reply = [block for block in blocks if not any(kw in block.lower() for kw in follow_up_keywords)]
        followup = [block for block in blocks if any(kw in block.lower() for kw in follow_up_keywords)]

        # Check if follow-up has already been sent
        if followup and self.has_answer_been_sent(chat_history, follow_up_keywords):
            followup = []

        return "\n\n".join(main_reply), "\n\n".join(followup)

    @staticmethod
    def has_answer_been_sent(history_messages: list, followup_keywords: list) -> bool:
        for msg in history_messages:
            if msg["role"] == "assistant":
                content_lower = msg["content"].lower()
                if any(kw in content_lower for kw in followup_keywords):
                    return True
        return False
