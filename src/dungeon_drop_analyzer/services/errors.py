"""Erros de domínio com mensagens em português para exibição na interface."""


class DomainError(Exception):
    """Base dos erros de regra de negócio."""


class ValidationError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class DuplicateError(DomainError):
    pass


class BackupError(DomainError):
    pass


class ExportError(DomainError):
    pass
