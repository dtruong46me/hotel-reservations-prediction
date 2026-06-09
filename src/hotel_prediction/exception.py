import sys
import traceback


class CustomException(Exception):
    """Custom exception that enriches the error message with file and line info."""

    def __init__(self, message: str, original_error: Exception):
        super().__init__(message)
        self.error_message = self._build_message(message, original_error)

    @staticmethod
    def _build_message(message: str, original_error: Exception) -> str:
        _, _, exc_tb = sys.exc_info()
        if exc_tb is not None:
            file_name = exc_tb.tb_frame.f_code.co_filename
            line_number = exc_tb.tb_lineno
            return (
                f"[{file_name} : line {line_number}] {message} "
                f"| Caused by: {type(original_error).__name__}: {original_error}"
            )
        return f"{message} | Caused by: {type(original_error).__name__}: {original_error}"

    def __str__(self) -> str:
        return self.error_message
