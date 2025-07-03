# -*- coding: utf-8 -*-
import re
import time
import traceback
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from cachetools import TTLCache

from Database.Connection import post_chat, get_chat_by_userid, get_follow_up_keywords
from Database.SheetConnection import get_user_existed_on_sheet
from Service.ChatService import IChatService
from Service.MessageService import MessageClient

# Caching setup
processed_message_ids = TTLCache(maxsize=10000, ttl=300)
message_buffers = defaultdict(list)
debounce_timers = {}
permission_cache = TTLCache(maxsize=10000, ttl=300)
DEBOUNCE_DELAY_SECONDS = 5


@dataclass
class ChatMessageHandler:
    chat_service: IChatService
    messenger: MessageClient
    fb_page_id: str

    def handle_entry(self, entry):
        for event in entry.get('messaging', []):
            self.handle_message_event(event)

    def handle_message_event(self, event):
        message = event.get('message', {})
        message_id = message.get('mid')
        message_text = message.get('text')
        sender_id = event['sender']['id']
        recipient_id = event['recipient']['id']

        if sender_id == recipient_id:
            print(f"📩 Ignored self-sent message from: {sender_id}")
            return

        print(f"📨 Received message_id: {message_id} | From: {sender_id} | Text: {message_text}")

        if message_id:
            if message_id in processed_message_ids:
                print(f"⚠️ Already processed message_id: {message_id}, skipping.")
                return
            processed_message_ids[message_id] = True
        else:
            print("⚠️ Message has no 'mid' — continuing anyway.")

        self.debounce_user_message(sender_id, message_text)

    def debounce_user_message(self, sender_id, message_text):
        if message_text and message_text not in message_buffers[sender_id]:
            message_buffers[sender_id].append(message_text)

        if sender_id in debounce_timers:
            debounce_timers[sender_id].cancel()

        debounce_timers[sender_id] = threading.Timer(
            DEBOUNCE_DELAY_SECONDS,
            self.debounce_process_message,
            args=(sender_id,)
        )
        debounce_timers[sender_id].start()

    def debounce_process_message(self, sender_id):
        raw_messages = message_buffers[sender_id]
        unique_messages = list(dict.fromkeys(raw_messages))
        full_message = "\n".join(unique_messages)
        message_buffers[sender_id].clear()

        if not full_message.strip():
            print(f"⚠️ Empty message from {sender_id}, skipping.")
            return

        if sender_id != self.fb_page_id and not self.get_user_existed_on_cached(
                sender_id) and not get_user_existed_on_sheet(sender_id):
            print(f"📝 Adding new user {sender_id} to sheet (message: {full_message})")
            self.set_cached_permission(sender_id)
            self.messenger.save_user(sender_id, True)

        if not self.get_cached_permission(sender_id) or sender_id == self.fb_page_id:
            return

        try:
            print(f"🤖 Sending message to ChatService from {sender_id}:\n{full_message}")
            response = self.chat_service.ask(full_message, sender_id)
            content = self.chat_service.convert_markdown_bold_to_unicode(response.get("content", ""))

            if response.get("function_call"):
                self.messenger.send_introduce_message(sender_id)
                time.sleep(2)
                self.messenger.send_image(sender_id)
                return

            text_part, json_part = self.split_text_and_json(content)

            if text_part == "booking":
                self.messenger.send_booking_message(sender_id, message_text=full_message)
                self.set_cached_permission(sender_id, False)
                return

            if json_part:
                self.messenger.send_message(sender_id, (text_part, json_part), full_message)
                return

            main, followup = self.split_main_and_followup(text_part, sender_id)

            post_chat(sender_id, [{"role": "user", "content": full_message}], is_update=True)
            self.messenger.send_message_with_no_logs(sender_id, main)
            post_chat(sender_id, [{"role": "assistant", "content": main}], is_update=False)

            if followup.strip():
                time.sleep(3)
                self.messenger.send_message_with_no_logs(sender_id, followup)
                post_chat(sender_id, [{"role": "assistant", "content": followup}], is_update=False)

        except Exception as e:
            print(f"❌ Error while processing message from {sender_id}: {e}")
            traceback.print_exc()

    @staticmethod
    def set_cached_permission(user_id, value=True):
        permission_cache[user_id] = value

    def get_cached_permission(self, user_id):
        if user_id in permission_cache:
            return permission_cache[user_id]
        permission = self.messenger.check_permission_auto_message(user_id)
        self.set_cached_permission(user_id, permission)
        return permission

    @staticmethod
    def get_user_existed_on_cached(user_id):
        return user_id in permission_cache

    @staticmethod
    def split_text_and_json(response_text):
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
        blocks = text.strip().split("\n\n")
        follow_up_keywords = get_follow_up_keywords()
        history = get_chat_by_userid(user_id)

        main = [b for b in blocks if not any(kw in b.lower() for kw in follow_up_keywords)]
        followup = [b for b in blocks if any(kw in b.lower() for kw in follow_up_keywords)]

        if followup and self.has_answer_been_sent(history, follow_up_keywords):
            followup = []

        return "\n\n".join(main), "\n\n".join(followup)

    @staticmethod
    def has_answer_been_sent(history_messages: list, followup_keywords: list) -> bool:
        return any(
            msg.get("role") == "assistant" and
            any(kw in msg.get("content", "").lower() for kw in followup_keywords)
            for msg in (history_messages or [])
        )
