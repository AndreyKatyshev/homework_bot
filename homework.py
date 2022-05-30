import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus
# from logging.handlers import RotatingFileHandler
from pprint import pprint

from exceptions import StatusCodeException, NotForSendException


load_dotenv()
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# handler = RotatingFileHandler(
#     'program.log', maxBytes=50000000, backupCount=5)
# logger.addHandler(handler)

# можно ли эти настройки перенести
# просто за условие if __name__ == '__main__':
# ещё я попробовал сделать функцию с настройками
# и вызвать её ниже но это не сработало, видимо так нельзя

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s - %(lineno)s',
    level=logging.DEBUG,
    filename='program.log',
    # hendlers=('program.log'),
    encoding="UTF-8",
    filemode='a'
)


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
        logging.info('Отправляем сообщение')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except NotForSendException:
        pass


def get_api_answer(current_timestamp):
    """делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    logging.info('начали запрос к API яндкс.практикума')
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        logging.error(f'упал запрос к эндпойнту: {ENDPOINT}')
        raise StatusCodeException(
            f'функции get_api_answer получила код: {response.status_code}'
            f'какая то причина из респонса ???'
            f'и какойто текст их контента ???'
        )
    return response.json()


def check_response(response: dict) -> list:
    """проверяет ответ API на корректность."""
    logging.info('начинаем проверку ответа от сервера')
    # как тут isinstance применить я не придумал
    # ведь нам нужно выбросить исключение в случае если тип НЕ словарь

    # с этой проверкой на проходит пайтест

    # if type(response) != dict:
    #     raise TypeException(
    #         'список домашек это не словарь')
    homework = response['homeworks']
    # homework = response.get('homeworks')
    # эта строчка не работает потому что
    # AttributeError: 'list' object has no attribute 'get'
    # хотя объект респонс это словарь а не список
    pprint(homework)
    print(type(homework))
    # непонятно как через isinstance
    if type(homework) != list:
        raise KeyError(
            'под ключом `homeworks` домашки приходят не в виде списка')
    return homework


def parse_status(homework):
    """Извлекает статус домашней работы.
    и формулирует строку сообщения для отправки.
    """
    # if not homework.get('homework_name'):
    #     raise TypeException(
    #         'нет названия у работы')
    # Я ПОХОДУ НЕ ПОНИМАЮ ЧТО ЗНАЧИТ ВЫБРОСИТЬ ИСКЛЮЧЕНИЕ
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """проверяет доступность переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    return False


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('отсутствуют обязательные переменные окружения')
        sys.exit()
    while True:
        current_report = {}
        prev_report = {}
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        try:
            current_timestamp = int(time.time())
            # как эта строчка может быть ниже респонса
            # если в респонсе выполняется функция
            # принимая current_timestamp как параметр
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks == []:
                logging.info('Список домашних работ пуст')
                # Если список домашек пустой, то шлём соответствующее
                # сообщение. куда шлём? логируем то есть?
                # или в телегу:
                # send_message(bot, 'Список домашних работ пуст')
            homework = homeworks[0]
            current_report['name'] = homework.get('homework_name')
            message = parse_status(homework)
            current_report['messages'] = message
            if current_report != prev_report:
                send_message(bot, message)
                logging.info('сообщение успешно отправлено')
            prev_report = current_report.copy()
            time.sleep(RETRY_TIME)
        except NotForSendException:
            logging.error('Сообщение не отправлено')
        except KeyError:
            logging.error('в словаре нет такого ключа')
        except IndexError:
            logging.error('в списке нет запрошенного элемента')
        # except Exception as error:
        #     message = f'Сбой в работе программы: {error}'
        #     logging.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
