import logging

# Custom logging level
SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")

# Color mapping
COLORS = {
    "INFO": "\033[36m",  # cyan
    "SUCCESS": "\033[32m",  # green
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",  # red
    "RESET": "\033[0m",
}


# Custom formatter
class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, COLORS["RESET"])
        message = super().format(record)
        return f"{color}{message}{COLORS['RESET']}"


# Configure logger
log = logging.getLogger("keysync")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter("[%(levelname)s] %(message)s"))
log.addHandler(handler)


# Add success helper
def success(self, message, *args, **kwargs):
    if self.isEnabledFor(25):
        self._log(25, message, args, **kwargs)


setattr(logging.Logger, "success", success)
