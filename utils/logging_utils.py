""" Logging utils.
"""
import logging
import os


def create_logger(logger_name):
    """ Create a logger with a defined name.

    :param logger_name: logger name
    :return: logger object
    """
    level = os.environ.get('LOGLEVEL', 'INFO')
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    _init_logger(logger, level, logger_name)
    return logger


def _init_logger(logger, level, file_name=None):
    file_name = logger.name if not file_name else file_name

    fh = logging.FileHandler('{}.log'.format(file_name))
    fh.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(filename)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
