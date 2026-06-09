"""
hotel_prediction.exception
==========================
Custom exception class with automatic traceback enrichment.

Reusable
--------
CustomException : Wrap any caught exception with file path and line number
                  context extracted from the active traceback.

Example
-------
::

    try:
        risky_operation()
    except Exception as exc:
        raise CustomException("risky_operation failed", exc) from exc
"""

from __future__ import annotations

import sys

__all__: list[str] = ["CustomException"]


# ── REUSABLE API ──────────────────────────────────────────────────────────────


class CustomException(Exception):
    """Enrich an exception message with the source file and line number.

    On construction the active ``sys.exc_info()`` traceback is inspected
    to extract the filename and line number where the exception originated.
    This information is prepended to the caller-supplied message so that
    log entries are self-contained even without a full traceback.

    Attributes:
        error_message: The enriched error string, including location and
                       the original exception type/value.

    Example:
        ::

            try:
                pd.read_csv("missing.csv")
            except Exception as exc:
                raise CustomException("Failed to load dataset", exc) from exc
    """

    def __init__(self, message: str, original_error: Exception) -> None:
        """Initialise with a human-readable message and the root cause.

        Args:
            message: Short description of what failed (written by the caller).
            original_error: The original exception that triggered this one.
        """
        super().__init__(message)
        self.error_message: str = self._build_message(message, original_error)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_message(message: str, original_error: Exception) -> str:
        """Construct the enriched error string.

        Args:
            message: Caller-supplied short description.
            original_error: Root-cause exception.

        Returns:
            A string of the form
            ``"[<file> : line <n>] <message> | Caused by: <Type>: <value>"``
            when traceback information is available, or a simpler two-part
            string when it is not (e.g. when raised outside an except block).
        """
        _, _, exc_tb = sys.exc_info()
        cause: str = f"{type(original_error).__name__}: {original_error}"
        if exc_tb is not None:
            file_name: str = exc_tb.tb_frame.f_code.co_filename
            line_number: int = exc_tb.tb_lineno
            return f"[{file_name} : line {line_number}] {message} | Caused by: {cause}"
        return f"{message} | Caused by: {cause}"

    # ── Dunder methods ────────────────────────────────────────────────────────

    def __str__(self) -> str:
        return self.error_message
