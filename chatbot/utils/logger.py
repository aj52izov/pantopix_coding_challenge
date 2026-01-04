import logging

class AnsiColorFormatter(logging.Formatter):
    def __init__(self, fmt, style='{'):
        super().__init__(fmt, style=style)
    def format(self, record: logging.LogRecord):
        no_style = '\033[0m'
        bold = '\033[1m'
        grey = '\033[90m'
        yellow = '\033[93m'
        red = '\033[31m'
        red_light = '\033[91m'
        start_style = {
            'DEBUG': grey,
            'INFO': no_style,
            'WARNING': yellow,
            'ERROR': red,
            'CRITICAL': red_light + bold,
        }.get(record.levelname, no_style)
        end_style = no_style
        return f'{start_style}{super().format(record)}{end_style}'
    
class Logger:
    """Logger class to handle logging with timestamps and colored output."""
    def __init__(self, name: str = __name__):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.timestamp_format = "%Y-%m-%d %H:%M:%S"
        handler = logging.StreamHandler()
        formatter = AnsiColorFormatter('{asctime} | {levelname:<8s} | {name:<20s} | {message}', style='{')
        handler.setFormatter(formatter)
        if not self.logger.hasHandlers():
            self.logger.addHandler(handler)
        
    def error(self, message: str):
        self.logger.error(f"{message}")
    
    def warning(self, message: str):
        self.logger.warning(f"{message}")
            
    def info(self, message: str):
        self.logger.info(f"{message}")    
        
    def debug(self, message: str):
        self.logger.debug(f"{message}")