"""Resource error module."""

import http

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Union


class Error(Exception):
    """
    Base class for resource errors.

    Each error class must expose the following attributes:
    • status: HTTP status code (integer)
    • phrase: HTTP reason phrase
    """


class ClientError(Error):
    """
    Base class for client resource errors.
    """


class ServerError(Error):
    """
    Base class for server resource errors.
    """


class _Errors:
    """
    Encapsulates resource error exception classes. Errors are dynamically generated from
    errors in the http.HTTPStatus enum.

    Errors can be accessed by HTTP status code or name.
    Example: fondat.error.errors[404] == fondat.error.errors.NotFoundError
    """

    def __init__(self):
        self._names = {}
        self._codes = {}
        for status in (s for s in http.HTTPStatus if 400 <= s.value <= 599):
            name = "".join(
                w.title() if w not in {"HTTP", "URI"} else w for w in status.name.split("_")
            )
            if not name.endswith("Error"):
                name += "Error"
            error = type(
                name,
                (ClientError if 400 <= status.value <= 499 else ServerError,),
                {
                    "status": status.value,
                    "phrase": status.phrase,
                    "__doc__": f"{status.description or status.phrase.capitalize()}.",
                },
            )
            self._names[name] = error
            self._codes[status.value] = error

    def __getitem__(self, code: int) -> Error:
        if error := self._codes.get(code):
            return error
        return InternalServerError

    def __getattr__(self, name: str) -> Error:
        if error := self._names.get(name):
            return error
        raise AttributeError

    def __iter__(self) -> Iterator[Error]:
        return iter(self._codes.values())


errors = _Errors()


# commonly used errors
BadRequestError = errors.BadRequestError
ForbiddenError = errors.ForbiddenError
InternalServerError = errors.InternalServerError
MethodNotAllowedError = errors.MethodNotAllowedError
NotFoundError = errors.NotFoundError
UnauthorizedError = errors.UnauthorizedError


@contextmanager
def replace(catch: Union[type, tuple[type]], throw: type, *args):
    """
    Return a context manager that catches exception(s) and raises a replacement exception. The
    replacement exception's arguments are the arguments of the caught exception, plus optional
    supplied arguments.

    Parameters:
    • catch: exception class or classes to catch
    • throw: exeption class to raise as the replacement
    • args: optional arguments to add to the thrown exception
    """
    try:
        yield
    except catch as cause:
        raise throw(*cause.args, *args) from cause


@contextmanager
def append(catch: Union[type, tuple[type]], value: str):
    """
    Return a context manager that catches exception(s), appends a string to the exception's
    message (first argument) and reraises the exception. If the caught exception has no
    arguments, then its first argument becomes the string to append.

    Parameters:
    • catch: exception class or classes to catch
    • value: string value to append to exception's first argument
    """
    try:
        yield
    except catch as c:
        if value is None:
            value = ""
        args = [value if not c.args else f"{c.args[0]}{value}"]
        if len(c.args) > 1:
            args += c.args[1:]
        c.args = tuple(args)
        raise
