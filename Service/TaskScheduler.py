from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from Database.Connection import get_all_chat
from Database.SheetConnection import set_user_follow_up_action
from Service.ChatService import OpenAIChatService, IChatService
from Service.MessageService import MessageClient


class TaskScheduler:
    def __init__(self, chatService: IChatService, message: MessageClient, recurring_time=60):
        self.recurring_time = recurring_time
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self.check_inactivity, 'interval', minutes=self.recurring_time)
        self.scheduler.start()
        print("🔁 Scheduler đã khởi động...")
        self.chatService = chatService
        self.message = message

    @staticmethod
    def parse_updated_at(updated_at_str):
        return datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))

    def send_reminder(self, user_id, hour_diff=5):
        gpt_message = self.chatService.ask_follow_up(user_id, hour_diff)
        self.message.send_message_with_no_logs(user_id, gpt_message.get('content', ''))
        set_user_follow_up_action(user_id, False)

    def check_inactivity(self, threshold_minutes=60):
        now = datetime.utcnow()
        for user_data in get_all_chat():
            last_update = user_data.get('updated_at')
            if now - last_update > timedelta(minutes=threshold_minutes) and self.message.check_permission_follow_up(
                    user_data.get('user_id')) and self.message.check_permission_auto_message(user_data.get('user_id')):
                self.send_reminder(user_data.get('user_id'), self.get_hour_diff(last_update))
            else:
                print(f"✔ User {user_data['user_id']} vẫn hoạt động hoặc follow-up tạm thời tắt.")

    @staticmethod
    def get_hour_diff(last_update):
        now = datetime.utcnow()
        return int((now - last_update).total_seconds() // 3600)
