import logging

def configure_logging(log_level=logging.INFO):
    """
    Configures the logging settings for the application.

    Args:
        log_level (int): The logging level to be set. Default is logging.INFO.
    """
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )