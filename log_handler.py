from logging import DEBUG, Logger, StreamHandler, getLogger

import colorlog


def get_logger(name: str) -> Logger:
    logger = getLogger(name)
    logger.setLevel(DEBUG)

    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)s:%(name)s:: %(message)s%(reset)s",
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )

    stream_handler = StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
