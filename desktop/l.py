import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()  # также выводим в консоль
    ]
)

# Использование
logger = logging.getLogger(__name__)
logger.info("Информационное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка")