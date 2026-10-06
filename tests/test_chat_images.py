import base64
import unittest

from chat_images import InvalidChatImage, validate_chat_image


class ChatImageValidationTests(unittest.TestCase):
    def test_accepts_supported_image_signatures(self):
        images = {
            "jpeg": b"\xff\xd8\xffdata",
            "png": b"\x89PNG\r\n\x1a\ndata",
            "gif": b"GIF89adata",
            "webp": b"RIFFxxxxWEBPdata",
        }
        mime_types = {
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        for image_type, data in images.items():
            with self.subTest(image_type=image_type):
                data_url = f"data:{mime_types[image_type]};base64,{base64.b64encode(data).decode()}"
                self.assertEqual(validate_chat_image(data_url), data_url)

    def test_rejects_unsupported_mime_and_mismatched_signature(self):
        with self.assertRaisesRegex(InvalidChatImage, "JPEG, PNG"):
            validate_chat_image("data:image/svg+xml;base64,PHN2Zz4=")
        with self.assertRaisesRegex(InvalidChatImage, "does not match"):
            validate_chat_image("data:image/png;base64," + base64.b64encode(b"not png").decode())

    def test_rejects_invalid_base64_and_oversized_payload(self):
        with self.assertRaisesRegex(InvalidChatImage, "data is invalid"):
            validate_chat_image("data:image/jpeg;base64,%%%")
        large_bytes = b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024)
        large_image = "data:image/jpeg;base64," + base64.b64encode(large_bytes).decode()
        with self.assertRaisesRegex(InvalidChatImage, "exceeds"):
            validate_chat_image(large_image)


if __name__ == "__main__":
    unittest.main()
