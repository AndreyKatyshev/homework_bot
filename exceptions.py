class NotForSendException(Exception):
    """Обрабатывает ошибки не предназначенные для отправки в телеграмм."""

    pass


class TypeException(NotForSendException):
    """Обрабатывает ошибку типа данных."""

    pass


class StatusCodeException(NotForSendException):
    """Обрабатывает ошибку кода ответа страницы."""

    pass


class ForSendImportantException(Exception):
    """Обрабатывает ошибки для отправки в телеграмм."""

    pass
