import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

from exceptions import NotForSendException, StatusCodeException, TypeException


load_dotenv()

logger = logging.getLogger(__name__)
StreamHandler = logging.StreamHandler()
StreamHandler.setLevel(logging.DEBUG)
FileHandler = RotatingFileHandler(
    filename='program.log', maxBytes=50000000, backupCount=5)
FileHandler.setLevel(logging.INFO)
logger.addHandler(StreamHandler)
logger.addHandler(FileHandler)

BASE_LOG_DIR = 'program.log'
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

# здесь название словаря предлагалось по умолчанию,
# я думаю что на нём тесты завязаны, но могу и пееименовать
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
    except NotForSendException as error:
        logging.info(f'Сообщение не отправлено: {error}')
        pass
    else:
        logging.info('Сообщение не отправлено! Ура, товарищи!')


def get_api_answer(current_timestamp):
    """делает запрос к эндпоинту API-сервиса."""
    try:
        logging.info('начали запрос к API яндкс.практикума')
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}
        dict_for_response = {
            'url': ENDPOINT,
            'headers': HEADERS,
            'params': params,
        }
        response = requests.get(**dict_for_response)
        if response.status_code != HTTPStatus.OK:
            raise StatusCodeException
    except StatusCodeException as error:
        logging.info(
            f'Запрос с параметрами {dict_for_response}, не прошёл'
            f'функции get_api_answer получила код: {response.status_code}'
            f'Какова причина остановки?: {response.reason}'
            f'ПРИЧИНА ОСТАНОВКИ??: {response.reason} !!!!'
            f'Текст {response.text}'
            f'ошибочка вышла: {error}'
        )
    else:
        logging.info('Шалость удалась, запрос от сервера получен')
        return response.json()


def check_response(response: dict) -> list:
    # не понял про аннотацию
    """проверяет ответ API на корректность."""
    logging.info('начинаем проверку ответа от сервера')
    if not isinstance(response, dict):
        raise TypeError(
            'список домашек это не словарь')
    if 'homeworks' and 'current_date' not in response:
        raise TypeException(
            'homeworks или current_date нет в запросе')
    homework = response['homeworks']
    if not isinstance(homework, list):
        raise KeyError(
            'под ключом `homeworks` домашки приходят не в виде списка')
    return homework


def parse_status(homework):
    """Извлекает статус домашней работы.
    и формулирует строку сообщения для отправки.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError(
            f'нет названия у работы {homework}')
    verdict = HOMEWORK_STATUSES[homework_status]
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(
            f'Статуса {homework_status} нет в словаре {HOMEWORK_STATUSES}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        # Почему иф нот?  логика же такова:
        # если Чек_токен вернул фолс
        # значит отсутствуют токены, скажем об этом
        logging.critical('отсутствуют обязательные переменные окружения')
        sys.exit('отсутствуют обязательные переменные окружения')
    current_report = {'name': '', 'messages': '', }
    prev_report: dict = current_report.copy()
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
                logging.info('Список домашних работ пуст')
            if current_report != prev_report:
                send_message(bot, message)
                prev_report = current_report.copy()
            else:
                logging.info('нет новых статусов')
        except NotForSendException:
            logging.error('Сообщение не отправлено')
        # except KeyError:
        #     logging.error('в словаре нет такого ключа')
        # except IndexError:
        #     logging.error('в списке нет запрошенного элемента')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':

    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s - %(lineno)s',
        level=logging.INFO,
        encoding="UTF-8",
        handlers=[
            RotatingFileHandler(
                BASE_LOG_DIR,
                mode='a',
                # он вроде по умолчанию стоит
                encoding="UTF-8",
                maxBytes=5000000,
                backupCount=5),
            logging.StreamHandler(stream=sys.stdout),
        ],
    )

    main()
