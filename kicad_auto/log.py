"""Log module

Handles logging initialization and formating.
"""
import sys
import logging

# Default domain, base name for the tool
domain = 'ki_auto'

def get_logger(name=None):
    """Get a module for a submodule or the root logger if no name is provided"""
    return logging.getLogger(domain+'.'+name) if name else logging.getLogger(domain)

def set_domain(name):
    """Set the base name for the tool"""
    global domain
    domain = name

def init(level):
    """Initialize the logging feature using a custom format and the specified verbosity level"""
    if level>=2:
       log_level=logging.DEBUG
    elif level==1:
       log_level=logging.INFO
    else:
       log_level=logging.WARNING

    logger=get_logger()
    logger.setLevel(log_level)
    ch = logging.StreamHandler()
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)

    return logger


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors"""

    if sys.stderr.isatty():
       grey = "\x1b[38;21m"
       yellow = "\x1b[93;1m"
       red = "\x1b[91;1m"
       bold_red = "\x1b[91;21m"
       cyan = "\x1b[36;1m"
       reset = "\x1b[0m"
    else:
       grey = ""
       yellow = ""
       red = ""
       bold_red = ""
       cyan = ""
       reset = ""
    #format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    format = "%(levelname)s:%(message)s (%(name)s - %(filename)s:%(lineno)d)"
    format_simple = "%(levelname)s:%(message)s"

    FORMATS = {
        logging.DEBUG: cyan + format + reset,
        logging.INFO: grey + format_simple + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
