import inspect
import logging
import os
import sys
import re

logger = logging.getLogger(__name__)

ERROR_MSG = "Something went wrong, please try again later!"
APP_NAME = "app"


def _get_caller_info(skip=2):
    """
    Returns full file path and line number of caller.
    skip=2 means:
        0 = this function
        1 = log wrapper
        2 = actual caller
    """
    try:
        frame = inspect.stack()[skip]
        full_path = os.path.abspath(frame.filename)
        line = frame.lineno
        return full_path, line
    except Exception:
        return "unknown", "unknown"
    
def handle_error_log(e, view_name, app_name, extra_values=None):
    try:
        # Try to extract traceback info first
        exc_type, exc_obj, exc_tb = sys.exc_info()

        if exc_tb is not None:
            full_path = os.path.abspath(exc_tb.tb_frame.f_code.co_filename)
            line = exc_tb.tb_lineno
        else:
            # No traceback (can happen in signal handlers)
            full_path, line = _get_caller_info(skip=2)

        logger.error(
            f"Error | File: {full_path} | "
            f"Line: {line} | "
            f"View: {view_name} | "
            f"Error: {str(e)} | "
            f"Extra: {extra_values}",
            extra={"AppName": app_name},
            exc_info=True,   # Proper stacktrace logging
        )

    except Exception as log_error:
        print("LOGGER FAILURE:", log_error)


def handle_info_log(msg, view_name, app_name, extra_values=None):
    try:
        full_path, line = _get_caller_info(skip=2)

        logger.info(
            f"Info | File: {full_path} | "
            f"Line: {line} | "
            f"View: {view_name} | "
            f"Message: {msg} | "
            f"Extra: {extra_values}",
            extra={"AppName": app_name},
        )

    except Exception as log_error:
        print("LOGGER FAILURE:", log_error)