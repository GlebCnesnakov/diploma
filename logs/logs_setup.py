import logging
import datetime

def setup_logging(timestamp=None):
    if timestamp is None:
        timestamp = datetime.datetime.now().strftime('%m-%d_%H-%M-%S-%f')

    logging.basicConfig(
        level=logging.INFO,
        format='%(name)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/log_{timestamp}.log'),

        ]
    )
    return timestamp

def get_logger(name):
    return logging.getLogger(name)