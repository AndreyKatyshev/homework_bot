import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus
from typing import Dict, List

from exceptions import (
    StatusCodeException, TypeException,
    TelegramError, ConectionError
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """отправляет сообщение в Telegram чат."""
    try:
        logging.info(f'Отправляем сообщение: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        raise TelegramError(f'Сообщение {message} не отправлено {error}')
    else:
        logging.info('Сообщение отправлено! Ура, товарищи!')


def get_api_answer(current_timestamp):
    """делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    dict_for_response = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params,
    }
    try:
        logging.info('начали запрос к API яндкс.практикума')
        response = requests.get(**dict_for_response)
        if response.status_code != HTTPStatus.OK:
            raise StatusCodeException(
                f'Запрос с параметрами {dict_for_response}, не прошёл'
                f'функции get_api_answer получила код: {response.status_code}'
                f'Какова причина остановки?: {response.reason}'
                f'Текст {response.text}'
            )
        return response.json()
    except Exception as error:
        raise ConectionError(
            f'проблема с подключением:{error}'
            f'Запрос выполняли вот с какими параметрами {dict_for_response}'
        )


def check_response(response: Dict) -> List:
    """проверяет ответ API на корректность."""
    logging.info('начинаем проверку ответа от сервера')
    if not isinstance(response, Dict):
        raise TypeError(
            'список домашек это не словарь')
    if 'homeworks' not in response or 'current_date' not in response:
        raise TypeException(
            'homeworks или current_date нет в запросе')
    homework = response.get('homeworks')
    if not isinstance(homework, List):
        raise KeyError(
            'под ключом `homeworks` домашки приходят не в виде списка')
    return homework


def parse_status(homework):
    """Извлекает статус домашней работы.
    и формулирует строку сообщения для отправки.
    """
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError(
            f'нет названия у работы {homework}')
    if homework_status not in HOMEWORK_STATUSES:
        raise ValueError(
            f'Статуса {homework_status} нет в словаре {HOMEWORK_STATUSES}')
    return(
        'Изменился статус проверки работы "{hw_name}" вердикт: {verdict}'.
        format(
            hw_name=homework.get('homework_name'),
            verdict=HOMEWORK_STATUSES[homework_status])
    )


def check_tokens():
    """проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID),)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'отсутствуют обязательные переменные окружения:'
            'PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID'
        )
        sys.exit('отсутствуют обязательные переменные окружения')
    current_report = {'name': '', 'messages': '', }
    prev_report: Dict = current_report.copy()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response['current_date']
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                current_report['name'] = homework.get('homework_name')
                message = parse_status(homework)
                current_report['messages'] = message
            else:
                current_report['messages'] = 'нет новых статусов'
            if current_report != prev_report:
                send_message(bot, message)
                prev_report = current_report.copy()
            else:
                logging.info('нет новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            current_report['messages'] = message
            if current_report != prev_report:
                send_message(bot, message)
                prev_report = current_report.copy()
            logging.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':

    BASE_LOG_DIR = 'program.log'

    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s - %(lineno)s',
        level=logging.DEBUG,
        encoding="UTF-8",
        handlers=[
            logging.FileHandler(f'{BASE_LOG_DIR}', 'a', 'utf-8'),
            logging.StreamHandler(stream=sys.stdout),
        ],
    )

    main()
