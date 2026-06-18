import logging
import re


class SecretAndPhoneFilter(logging.Filter):
    PHONE = re.compile(r"(?:\+?38)?0\d{9}")
    SECRET = re.compile(r"(?i)(api[_-]?key|token|service[_-]?role[_-]?key)=([^\s]+)")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        message = self.PHONE.sub("+380******XXX", message)
        message = self.SECRET.sub(r"\1=***", message)
        record.msg, record.args = message, ()
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(SecretAndPhoneFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
