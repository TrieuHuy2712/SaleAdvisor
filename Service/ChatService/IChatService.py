from abc import ABC, abstractmethod


class IChatService(ABC):
    @abstractmethod
    def ask(self, user_input: str, user_id: str) -> dict:
        """
        Gửi tin nhắn và nhận phản hồi từ AI.
        """
        pass

    @abstractmethod
    def ask_follow_up(self, user_id: str, hour_diff: int) -> dict:
        """
        Gửi tin nhắn theo dõi và nhận phản hồi từ AI.
        """
        pass
