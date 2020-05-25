"""
This code is taken from StackOverflow

https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output

Thanks man!
"""
import logging

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

# The background is set with 40 plus the number of the color, and the foreground with 30

# These are the sequences need to get colored ouput
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"


def formatter_message(message, use_color=True):
    if use_color:
        message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message


COLORS = {
    "WARNING": YELLOW,
    "INFO": WHITE,
    "DEBUG": BLUE,
    "CRITICAL": YELLOW,
    "ERROR": RED,
}


class ColoredFormatter(logging.Formatter):
    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = (
                COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
            )
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


class NoMoreReferencing(logging.Filter):
    def __init__(self):
        super().__init__(name="discord.state")

    def filter(self, record):
        if record.levelname == "WARNING" and "referencing an unknown" in record.msg:
            return False
        return True


class NoMoreRatelimit(logging.Filter):
    def __init__(self):
        super().__init__(name="discord.http")

    def filter(self, record):
        if record.levelname == "WARNING" and "rate limit" in record.msg:
            return False
        return True


logging.getLogger("discord.state").addFilter(NoMoreReferencing())
logging.getLogger("discord.http").addFilter(NoMoreRatelimit())

FORMAT = (
    "[$BOLD%(name)-20s$RESET][%(levelname)-18s]  %(message)s"
    " ($BOLD%(filename)s$RESET:%(lineno)d)"
)
COLOR_FORMAT = formatter_message(FORMAT, True)
logging.root.setLevel(logging.INFO)
color_formatter = ColoredFormatter(COLOR_FORMAT)
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
stream.setFormatter(color_formatter)


def file_handler(id_):
    file_handler_ = logging.FileHandler(
        filename=f"idlerpg-{id_}.log", encoding="utf-8", mode="w"
    )
    file_handler_.setFormatter(color_formatter)
    return file_handler_
