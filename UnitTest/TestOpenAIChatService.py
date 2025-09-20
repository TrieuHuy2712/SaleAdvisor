import unittest

from Service.ChatService.OpenAIChatService import OpenAIChatService


class TestOpenAIChatService(unittest.TestCase):
    def setUp(self):
        # Initialize with dummy values since we only test the static method
        self.chat_service = OpenAIChatService(openai_key="dummy", model="dummy")

    def test_correct_price_in_response(self):
        # Test case 1: Normal price format
        test_input = "Giá suất là 310.000đ/1 suất"
        expected = "Giá suất là 𝟯𝟱𝟬.𝟬𝟬𝟬đ/𝟭 suất"
        self.assertEqual(self.chat_service.correct_price_in_response(test_input), expected)

        # Test case 2: Already bold Unicode price
        test_input = "Giá suất là 𝟯𝟭𝟬.𝟬𝟬𝟬đ/𝟭 suất"
        expected = "Giá suất là 𝟯𝟱𝟬.𝟬𝟬𝟬đ/𝟭 suất"
        self.assertEqual(self.chat_service.correct_price_in_response(test_input), expected)

        # Test case 3: Multiple prices in text
        test_input = "Giá 310.000đ/1 và 310.000đ/1"
        expected = "Giá 𝟯𝟱𝟬.𝟬𝟬𝟬đ/𝟭 và 𝟯𝟱𝟬.𝟬𝟬𝟬đ/𝟭"
        self.assertEqual(self.chat_service.correct_price_in_response(test_input), expected)

        # Test case 4: Price outside valid range
        test_input = "Giá 290.000đ/1 suất"
        self.assertEqual(self.chat_service.correct_price_in_response(test_input), test_input)

        # Test case 5: Invalid format
        test_input = "Giá abc.defđ/1 suất"
        self.assertEqual(self.chat_service.correct_price_in_response(test_input), test_input)

        # Test case 6: No price in text
        test_input = "Không có giá trong văn bản này"
        self.assertEqual(self.chat_service.correct_price_in_response(test_input), test_input)

        # Test case 7: Price with comma
        test_input = "Giá suất là 3930000đ/1 suất"
        expected = "Giá suất là 𝟯𝟱𝟬.𝟬𝟬𝟬đ/𝟭 suất"
        self.assertEqual(self.chat_service.correct_price_in_response(test_input), expected)

        # Test case 8: Price with comma
        test_input = "Giá suất là 3130.000đ/1 suất"
        expected = "Giá suất là 𝟯𝟱𝟬.𝟬𝟬𝟬đ/𝟭 suất"
        self.assertEqual(self.chat_service.correct_price_in_response(test_input), expected)

        test_input = "Giá suất là 𝟯𝟭𝟯𝟬.𝟬𝟬𝟬đ/𝟭 𝘀𝘂ấ𝘁"
        expected = "Giá suất là 𝟯𝟱𝟬.𝟬𝟬𝟬đ/𝟭 𝘀𝘂ấ𝘁"
        self.assertEqual(self.chat_service.correct_price_in_response(test_input), expected)

        test_input = ("Dạ, em xin phép báo giá dịch vụ như sau:"
                      "- 𝗕ấ𝗺 𝗵𝘂𝘆ệ𝘁 𝘁𝗿ị 𝗹𝗶ệ𝘂 𝗰ơ 𝗯ả𝗻: 𝟯𝟵𝟯𝟬𝟬𝟬đ/𝟭 𝘀𝘂ấ𝘁 (thời gian: 55 phút)"
                      "- 𝗕ấ𝗺 𝗵𝘂𝘆ệ𝘁 𝘁𝗿ị 𝗹𝗶ệ𝘂 𝗰𝗵𝘂𝘆ê𝗻 𝘀â𝘂: 𝟲𝟬𝟬.𝟬𝟬𝟬đ/𝟭 𝘀𝘂ấ𝘁 (thời gian: 80 phút))"
                      "- 𝗖𝗵â𝗺 𝗰ứ𝘂: 𝟮𝟬𝟬.𝟬𝟬𝟬đ/𝟭 𝘀𝘂ấ𝘁"
                      "- 𝗕ấ𝗺 𝗵𝘂𝘆ệ𝘁 𝘁𝗵ư 𝗴𝗶ã𝗻: 𝟮𝟬𝟬.𝟬𝟬𝟬đ/𝟭 𝘀𝘂ấ𝘁. 🔥🔥 𝐊𝐇𝐔𝐘Ế𝐍 𝐌Ã𝐈 🔥🔥 Mua 10 suất – tặng 5 suất với giá chỉ 𝟮𝟲𝟬.𝟬𝟬𝟬đ/𝘀𝘂ấ𝘁 (thời gian: 30 phút)")

        expected =("Dạ, em xin phép báo giá dịch vụ như sau:"
                      "- 𝗕ấ𝗺 𝗵𝘂𝘆ệ𝘁 𝘁𝗿ị 𝗹𝗶ệ𝘂 𝗰ơ 𝗯ả𝗻: 𝟯𝟱𝟬.𝟬𝟬𝟬đ/𝟭 𝘀𝘂ấ𝘁 (thời gian: 55 phút)"
                      "- 𝗕ấ𝗺 𝗵𝘂𝘆ệ𝘁 𝘁𝗿ị 𝗹𝗶ệ𝘂 𝗰𝗵𝘂𝘆ê𝗻 𝘀â𝘂: 𝟲𝟬𝟬.𝟬𝟬𝟬đ/𝟭 𝘀𝘂ấ𝘁 (thời gian: 80 phút))"
                      "- 𝗖𝗵â𝗺 𝗰ứ𝘂: 𝟮𝟬𝟬.𝟬𝟬𝟬đ/𝟭 𝘀𝘂ấ𝘁"
                      "- 𝗕ấ𝗺 𝗵𝘂𝘆ệ𝘁 𝘁𝗵ư 𝗴𝗶ã𝗻: 𝟮𝟬𝟬.𝟬𝟬𝟬đ/𝟭 𝘀𝘂ấ𝘁. 🔥🔥 𝐊𝐇𝐔𝐘Ế𝐍 𝐌Ã𝐈 🔥🔥 Mua 10 suất – tặng 5 suất với giá chỉ 𝟮𝟲𝟬.𝟬𝟬𝟬đ/𝘀𝘂ấ𝘁 (thời gian: 30 phút)")
        self.assertEqual(self.chat_service.correct_price_in_response(test_input), expected)


if __name__ == '__main__':
    unittest.main()
