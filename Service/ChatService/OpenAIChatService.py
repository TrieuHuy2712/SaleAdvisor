import openai
from dataclasses import dataclass

from Database.Connection import get_functions, get_faq, get_chat_by_userid, get_welcome_prompt, get_prompt, \
    get_follow_up_prompt, get_classify_prompt
from Service.ChatService.IChatService import IChatService


@dataclass
class OpenAIChatService(IChatService):
    openai_key: str
    model: str

    def __post_init__(self):
        openai.api_key = self.openai_key

    def ask(self, user_input: str, user_id: str) -> dict:
        # Classify the message
        classification = self.classify_message_with_prompt(user_input)
        if classification == "booking":
            return {"content": "booking"}

        # Prepare data
        functions = get_functions()
        faq_data = self.filter_faq_data(get_faq())
        chat_history = get_chat_by_userid(user_id=user_id)  # should return list of messages or None

        welcome_prompt = get_welcome_prompt() + "\n" if not chat_history else ""

        # System prompt with FAQ
        system_message = {
            "role": "system",
            "content": get_prompt() + "\n" +
                       welcome_prompt + "Các thông tin FAQ có sẵn là:\n" +
                       '\n'.join([f"{k}: {v}" for k, v in faq_data.items()])
        }

        # Build messages list
        messages = [system_message]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_input})

        # Send to OpenAI
        response = openai.ChatCompletion.create(
            model=self.model,  # Đổi từ gpt-4-turbo
            functions=functions,
            function_call="auto",
            messages=messages,
            temperature=0.7,
            # max_tokens=150,
        )

        return response['choices'][0]['message']

    def ask_follow_up(self, user_id: str, hour_diff: int) -> dict:
        """
        Gửi câu hỏi tiếp theo đến OpenAI với lịch sử trò chuyện đã lưu.
        """
        chat_history = get_chat_by_userid(user_id=user_id)
        if not chat_history:
            raise ValueError("Không có lịch sử trò chuyện để gửi câu hỏi tiếp theo.")

        # System prompt với FAQ
        system_message = {
            "role": "system",
            "content": get_follow_up_prompt().format(
                hours_passed=hour_diff,
                history_text="\n".join(f"{item['role']}: {item['content']}" for item in chat_history if
                                       'content' in item and 'role' in item)
            )
        }

        # Xây dựng danh sách tin nhắn
        messages = [system_message]

        # Gửi đến OpenAI
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
        )

        return response['choices'][0]['message']

    @staticmethod
    def classify_message_with_prompt(message: str) -> str:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": get_classify_prompt()},
                {"role": "user", "content": message}
            ],
            temperature=0
        )
        reply = response.choices[0].message['content'].strip().lower()
        return reply

    @staticmethod
    def detect_english_language_message(message: str) -> bool:
        """
        Phát hiện ngôn ngữ của tin nhắn.
        """
        prompt = f'Is the following sentence written entirely in English (without any Vietnamese words or structure)? Answer only "true" or "false". Sentence: "{message}"'
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a language detector that only answers 'true' or 'false'."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=5,  # chỉ cần 1 từ: true hoặc false
            timeout=5,  # giới hạn thời gian, nếu quá thì raise exception
            temperature=0
        )
        return response.choices[0].message["content"].strip().lower() == "true"

    def filter_faq_data(self, data) -> dict:
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
                faq_data[question] = self.combine_list_dict(answer)

            else:
                faq_data[question] = answer

        return faq_data

    @staticmethod
    def combine_list_dict(data) -> list:
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
