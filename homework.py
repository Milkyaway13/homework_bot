import os
import sys
import time
import logging
from http import HTTPStatus

import requests
from json import JSONDecodeError
import telegram
from dotenv import load_dotenv

from exceptions import (
    TelegramMessageError, ResponseStatusError, JsonFormatError)


load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

logging.basicConfig(
    filename="program.log",
    format='''%(asctime)s - %(name)s - %(levelname)s
              - %(message)s - line:%(lineno)d''',
    encoding="utf-8",
    level=logging.INFO,
)


def check_tokens():
    """Проверка наличия переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Функция отправки сообщения в чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug("Сообщение отправлено.")
    except telegram.error.Unauthorized as error:
        message = f"Ошибка при отправке сообщения в телеграм: {error}"
        logging.error(message)
        raise TelegramMessageError(message)


def get_api_answer(timestamp):
    """Запрос к эндпоинту и получение ответа."""
    payload = {"from_date": timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            message = (
                f"Эндпоинт {ENDPOINT} недоступен. "
                "Api вернула ответ, отличный от 200"
            )
            logging.error(message)
            raise ResponseStatusError(message)
        return response.json()

    except requests.exceptions.RequestException as error:
        logging.error(f"Сбой в работе программы: {error}")
        return None

    except JSONDecodeError as error:
        message = f"{error}: Полученный ответ не соовтетствует формату JSON"
        logging.error(message)
        raise JsonFormatError(message)


def check_response(response):
    """Функция проверки получения ответа от API."""
    try:
        homeworks = response["homeworks"]
        if not isinstance(homeworks, list):
            logging.error("Значение ключа 'homeworks' должно быть списком.")
            raise TypeError("Значение ключа 'homeworks' должно быть списком.")
        return homeworks
    except KeyError:
        logging.error("Ответ API не содержит ключа 'homeworks'.")
        raise KeyError("Ответ API не содержит ключа 'homeworks'.")


def parse_status(homework):
    """Функция для получения информации о конкретной домашке."""
    try:
        homework_name = homework["homework_name"]
        status = homework["status"]

        if status not in HOMEWORK_VERDICTS:
            logging.error(
                f"Недокументированный статус домашней работы: {status}")
            raise ValueError(
                f"Недокументированный статус домашней работы: {status}")

        verdict = HOMEWORK_VERDICTS[status]
        logging.info(
            f'Изменился статус проверки работы "{homework_name}". {verdict}')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as e:
        logging.error(f"Ответ API не содержит ключа: {e}")
        raise ValueError(f"Ответ API не содержит ключа: {e}")
    except TypeError:
        logging.error("Неправильный формат ответа API.")
        raise ValueError("Неправильный формат ответа API.")


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical("Отсутствуют обязательные переменные окружения!")
        sys.exit()
    logging.info("Начало работы программы")
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_report = {"name": "", "status": ""}
    prev_report = current_report.copy()

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if homeworks:
                new_status = homeworks[0]["status"]
                current_homework_name = homeworks[0]["homework_name"]

                current_report["name"] = current_homework_name
                current_report["status"] = new_status

                if current_report != prev_report:
                    verdict = HOMEWORK_VERDICTS.get(new_status)
                    if verdict:
                        message = (
                            'Изменился статус проверки работы "{}". '
                            '{}'.format(current_homework_name, verdict)
                        )
                        logging.info(message)
                        send_message(bot, message)
                    else:
                        message = (
                            "Недокументированный статус домашней работы:"
                            f"{new_status}"
                        )
                        logging.error(message)
                        send_message(bot, message)

                prev_report = current_report.copy()

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logging.error(message)
            send_message(bot, message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
