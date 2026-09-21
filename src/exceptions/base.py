"""Framework-independent application exceptions with reviewed public messages."""


class DomainError(Exception):
    """Constructor details remain private; handlers expose only public_detail."""

    public_detail = "The operation could not be completed."
