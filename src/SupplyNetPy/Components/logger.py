import logging
class GlobalLogger:
    """
    A simple logger class that allows logging messages to the screen or to a file.
    Logging can be turned on or off.

    Parameters:
        log_to_file (bool): Whether to log messages to a file.
        log_file (str): The file to which log messages will be written.
        log_to_screen (bool): Whether to log messages to the screen.
    """
    def __init__(self, logger_name='sim_trace', log_to_file=True, log_file='simulation_trace.log', log_to_screen=True):
        """
        Initializes the Logger with options to log to file, log file name, and log to screen.

        Parameters:
            log_to_file (bool): Whether to log messages to a file. Defaults to False.
            log_file (str): The file to which log messages will be written. Defaults to 'app.log'.
            log_to_screen (bool): Whether to log messages to the screen. Defaults to True.
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)

        self.log_to_file = log_to_file
        self.log_to_screen = log_to_screen

        self.log_file = log_file
        self.configure_logger()
    
    def set_log_file(self,filename):
        """
        Sets given log file to write simulation logs
        """
        self.log_file = filename
        self.configure_logger()

    def get_log_file(self):
        """
        Returns current log file name (path) in which simulation logs are written
        """
        return self.log_file

    def set_logger(self,logger_name):
        """
        Sets given logger name to write simulation logs
        """
        self.logger = logging.getLogger(logger_name)

    def configure_logger(self):
        """
        Configures the logger by adding handlers based on user preferences.
        """
        self.logger.handlers = []

        if self.log_to_screen:
            screen_handler = logging.StreamHandler()
            screen_handler.setLevel(logging.DEBUG)
            screen_format = logging.Formatter('%(levelname)s %(asctime)s %(name)s - %(message)s')
            screen_handler.setFormatter(screen_format)
            self.logger.addHandler(screen_handler)

        if self.log_to_file:
            file_handler = logging.FileHandler(self.log_file, mode='w')
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter('%(levelname)s %(asctime)s %(name)s - %(message)s')
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)

    def log(self, level, message):
        """
        Logs a message at the specified level.

        Parameters:
            level (str): The level at which to log the message. 
                         Can be 'debug', 'info', 'warning', 'error', or 'critical'.
            message (str): The message to log.
        """
        if self.logger.handlers:
            if level == 'debug':
                self.logger.debug(message)
            elif level == 'info':
                self.logger.info(message)
            elif level == 'warning':
                self.logger.warning(message)
            elif level == 'error':
                self.logger.error(message)
            elif level == 'critical':
                self.logger.critical(message)

    def enable_logging(self,log_to_file=True,log_to_screen=True):
        """
        Enables logging by configuring the logger with the appropriate handlers.
        """
        self.log_to_file = log_to_file
        self.log_to_screen = log_to_screen
        self.configure_logger()

    def disable_logging(self):
        """
        Disables logging by clearing all handlers from the logger.
        """
        self.logger.handlers = []