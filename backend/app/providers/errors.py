"""Provider boundary errors that handlers/runtime must interpret."""


class RecoverableProviderError(Exception):
    """Transient provider failure; keep checkpoints and continue the same task later."""
