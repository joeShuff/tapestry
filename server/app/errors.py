"""Domain errors. The service layer raises these; the web layer maps them to HTTP."""


class DomainError(Exception):
    status = 400


class NotFound(DomainError):
    status = 404


class InvalidInput(DomainError):
    status = 400


class UnsupportedMedia(DomainError):
    status = 415
