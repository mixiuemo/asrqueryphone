import os
import logging
from logging.handlers import TimedRotatingFileHandler
import platform

class Logger:
    def __init__(self, log_dir="ttsLogs", log_filename="log.log"):
        os.makedirs(log_dir, exist_ok=True)
        full_path = os.path.join(log_dir, log_filename)

        self.logger = logging.getLogger("TTSLogger")
        self.logger.setLevel(logging.INFO)

        handler = TimedRotatingFileHandler(
            filename=full_path,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8"
        )
        handler.suffix = "%Y-%m-%d"
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def info(self, *args):
        self.logger.info(" ".join(map(str, args)))

    def warning(self, *args):
        self.logger.warning(" ".join(map(str, args)))

    def error(self, *args):
        self.logger.error(" ".join(map(str, args)))
