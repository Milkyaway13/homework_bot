from dataclasses import dataclass


@dataclass
class TelegramMessageError(Exception):
    """Ошибка при отправке сообщения."""
    message: str


@dataclass
class ResponseStatusError(Exception):
    """Ошибка при получении статуса кода."""
    message: str


@dataclass
class JsonFormatError(Exception):
    """Ошибка при получении неверного формата данных."""
    message: str
