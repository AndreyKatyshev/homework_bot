import logging
import os
import requests
import time
import telegram

from exceptions import TypeException, StatusCodeException

from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s - %(lineno)s',
    level=logging.DEBUG,
    filename='program.log',
    encoding="UTF-8",
    filemode='w'
)

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
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """делает запрос к эндпоинту API-сервиса."""
    # timestamp = current_timestamp or int(time.time())
    timestamp = current_timestamp or 1651708800
    params = {'from_date': timestamp}
    url = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise StatusCodeException(
            'функции get_api_answer получила код, отличный от 200')
    print(response.status_code)
    return response.json()


def check_response(response):
    """проверяет ответ API на корректность."""
    homework = response['homeworks']
    logging.debug(pprint(homework))
    # pprint(homework)
    # print(type(homework))
    if type(homework) != list:
        raise TypeException(
            'под ключом `homeworks` домашки приходят не в виде списка')
    return homework


def parse_status(homework):
    """Извлекает статус домашней работы.
    и формулирует строку сообщения для отправки.
    """
    # homework_name = homework['homework_name']
    # homework_status = homework['status']
    # Запомни два варианта обращения к значениям словаря по ключу
    # Две строчки выше равны двум ниже
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    print(message)
    return message


def check_tokens():
    """проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    logging.critical('отсутствуют обязательные переменные окружения')
    return False


def main():
    """Основная логика работы бота."""
    while True:
        try:
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            # current_timestamp = int(time.time())
            current_timestamp = 1651708800
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            homework = homeworks[0]
            # pprint(homework)
            # Печатаем последнюю работу
            message = parse_status(homework)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Сбой в работе программы: {error}')
            time.sleep(RETRY_TIME)
        else:
            False


if __name__ == '__main__':
    main()
