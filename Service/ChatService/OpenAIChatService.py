import re

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

        formatted_faq_text = self.format_faq_data(faq_data)

        # System prompt with FAQ
        system_message = {
            "role": "system",
            "content": get_prompt() + "\n" +
                       welcome_prompt + "Các thông tin FAQ có sẵn là:\n" +
                       formatted_faq_text
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

        reply = response['choices'][0]['message']
        content = reply.get("content", "")
        content = self.correct_price_in_response(content)
        reply["content"] = content

        return reply

    @staticmethod
    def correct_price_in_response(text: str) -> str:
        # Thay mọi giá sai thuộc dạng 3xx.000đ/1 suất thành 350.000đ/1 suất
        text = re.sub(
            r"\b3\d{2}\.000đ/1 suất\b",  # bắt đúng pattern giá 3xx.000đ/1 suất
            "350.000đ/1 suất",
            text
        )

        # Có thể thêm tương tự cho các giá khác nếu cần
        return text

    @staticmethod
    def parse_faq_entry(entry: str) -> dict:
        parts = entry.split(',')
        result = {}
        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                result[key.strip()] = value.strip()
        return result

    def format_faq_data(self, faq_data: dict) -> str:
        lines = []
        for key, value in faq_data.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    parsed = self.parse_faq_entry(item)
                    name = parsed.get("tên", "")
                    price = parsed.get("giá", "")
                    duration = parsed.get("thời_gian", "")
                    line = f"- {name}: {price}"
                    if duration:
                        line += f" (thời gian: {duration})"
                    lines.append(line)
            else:
                lines.append(f"{key}: {value}")
            lines.append("")  # dòng trống giữa các nhóm
        return "\n".join(lines)

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
        prompt = (
            'Answer only true or false.\n'
            'Is the sentence written entirely in English, with no Vietnamese words or grammar?\n\n'
            f'Sentence: "{message}"'
        )
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
        print(f"🔍 Language detection response: {response.choices[0].message['content'].strip()}")
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

    @staticmethod
    def bold_unicode(text):
        normal_to_bold = {
            'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲',
            'f': '𝗳', 'g': '𝗴', 'h': '𝗵', 'i': '𝗶', 'j': '𝗷',
            'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼',
            'p': '𝗽', 'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁',
            'u': '𝘂', 'v': '𝘃', 'w': '𝘄', 'x': '𝘅', 'y': '𝘆', 'z': '𝘇',
            'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘',
            'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝',
            'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢',
            'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧',
            'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
            '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰',
            '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵',
            ' ': ' ', '.': '.', ',': ',', ':': ':', '?': '?', '!': '!'

        }
        return ''.join([normal_to_bold.get(c, c) for c in text])

    def convert_markdown_bold_to_unicode(self, message):
        # Tìm đoạn **bold**
        def repl(match):
            return self.bold_unicode(match.group(1))

        return re.sub(r"\*\*(.+?)\*\*", repl, message)
