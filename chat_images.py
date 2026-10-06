import base64
import binascii


MAX_CHAT_IMAGE_BYTES = 5 * 1024 * 1024
MAX_CHAT_IMAGE_DATA_URL_LENGTH = 7_100_000
IMAGE_PREFIXES = {
    "data:image/jpeg;base64,": ("jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "data:image/png;base64,": ("png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "data:image/gif;base64,": ("gif", lambda data: data.startswith((b"GIF87a", b"GIF89a"))),
    "data:image/webp;base64,": (
        "webp",
        lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    ),
}


class InvalidChatImage(ValueError):
    pass


def validate_chat_image(data_url):
    if not isinstance(data_url, str):
        raise InvalidChatImage("The attached image data is invalid.")
    prefix = next((item for item in IMAGE_PREFIXES if data_url.startswith(item)), None)
    if prefix is None:
        raise InvalidChatImage("Attach a JPEG, PNG, WebP, or GIF image.")
    if len(data_url) > MAX_CHAT_IMAGE_DATA_URL_LENGTH:
        raise InvalidChatImage("The attached image exceeds the upload limit.")
    encoded = data_url[len(prefix):]
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise InvalidChatImage("The attached image data is invalid.") from error
    if not image_bytes or len(image_bytes) > MAX_CHAT_IMAGE_BYTES:
        raise InvalidChatImage("The attached image exceeds the upload limit.")
    _, signature_matches = IMAGE_PREFIXES[prefix]
    if not signature_matches(image_bytes):
        raise InvalidChatImage("The attached image format does not match its data.")
    return data_url
