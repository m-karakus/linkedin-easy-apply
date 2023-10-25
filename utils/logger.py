import json
import traceback
import os
import sys
import logging
import time
from datetime import datetime

# current = os.path.dirname(os.path.realpath(__file__))
# parent = os.path.dirname(current)
# sys.path.append(parent)
# from config import ROOT_DIR

LOG_LEVEL = os.getenv("LOG_LEVEL") or "INFO"

log_levels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

default_log_level = log_levels.get(LOG_LEVEL.lower())
default_extra = { "function" :"","f_args": "", "f_kwargs" :""} 

class Logger:
    def __init__(self) -> None:
        """
        Custom Usage:
        logger = Logger()
        msg = "This is a log message"
        logger.log(msg,log_level="error")
        or 
        logger.error("This is an error message")
        """
        self.logger = logging.getLogger("logger")
        if not self.logger.handlers:

            # create the handlers and call logger.addHandler(logging_handler)       
            self.logger = logging.getLogger("logger")
            # self.logger.setLevel(logging.DEBUG)
            self.logger.setLevel(default_log_level)

            # Create a formatter
            # https://docs.python.org/3/library/logging.html#logrecord-attributes
            
            frmt = '''{"timestamp" : "%(asctime)s", "level" : "%(levelname)s", "levelno" : "%(levelno)s", "message" : %(message)s, "function" : "%(function)s", "f_args" : "%(f_args)s", "f_kwargs" : "%(f_kwargs)s" }'''
            json_formatter = logging.Formatter(frmt)
            json_formatter.converter = time.gmtime # set timezone as gmtime

            frmt = "%(asctime)s | %(levelname)s | %(levelno)s | %(message)s | %(function)s"
            string_formatter = logging.Formatter(frmt)
            string_formatter.converter = time.gmtime # set timezone as gmtime
            
            # Create a file handler
            path = os.path.abspath(os.path.join("logs"))
            if not os.path.isdir(path):
                os.mkdir(path)
            date = datetime.today().strftime("%Y%m%d")
            if not os.path.exists(path):
                os.makedirs(path)
            file_path = os.path.abspath(os.path.join(path, "log_{date}.log".format(date=date)))
            fh = logging.FileHandler(file_path,mode="a",encoding="utf8")
            
            # fh.setLevel(logging.DEBUG)
            fh.setLevel(default_log_level)
            fh.setFormatter(string_formatter)

            # Create a console handler
            ch = logging.StreamHandler()
            # ch.setLevel(logging.ERROR)
            ch.setLevel(default_log_level)
            ch.setFormatter(json_formatter)

            # Add handlers to the logger
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def message_formatter(self,message):
        msg = json.dumps(str(message))
        return msg

    def log(self,message,log_level="info",extra=default_extra):
        msg = self.message_formatter(message)

        logger = self.logger
        if log_level == "debug":
            logger.debug(msg, extra=extra)
        elif log_level == "info":
            logger.info(msg, extra=extra)
        elif log_level == "warning":
            logger.warning(msg, extra=extra)
        elif log_level == "error":
            logger.error(msg, extra=extra)
        elif log_level == "critical":
            logger.critical(msg, extra=extra)
        else:
            logger.exception(msg, extra=extra)
        return
    
    def debug(self, message, extra=default_extra):
        msg = self.message_formatter(message)
        logger = self.logger
        logger.debug(msg,extra=extra)
        return
    
    def info(self, message, extra=default_extra):
        msg = self.message_formatter(message)
        logger = self.logger
        logger.info(msg,extra=extra)
        return
        
    def warning(self, message, extra=default_extra):
        msg = self.message_formatter(message)
        logger = self.logger
        logger.warning(msg,extra=extra)
        return
    
    def error(self, message, extra=default_extra):
        msg = self.message_formatter(message)
        logger = self.logger
        logger.error(msg,extra=extra)
        return
        
    def critical(self, message, extra=default_extra):
        msg = self.message_formatter(message)
        logger = self.logger
        logger.critical(msg,extra=extra)
        return

def log_container(func):
    def wrapper(*args, **kwargs):
        # Log some messages
        logger = Logger()
        extra = { 
                "function" :func.__name__,
                "f_args": args, 
                "f_kwargs" :kwargs
            } 
        try:
            # send start message
            message = "Started"
            logger.log(message,extra=extra, log_level="debug")

            # call the function
            result = func(*args, **kwargs)
            
            # send end message
            # msg["msg"] = "Ended"
            # logger.log(msg,extra=extra)
            
            return result
    
        except Exception as e:
            message = str(e) + str(traceback.format_exc()).replace("\n"," ")
            logger.log(message,log_level="error",extra=extra)
    
    return wrapper


