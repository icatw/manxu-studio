"""Provider boundary errors that handlers/runtime must interpret."""


class ProviderControlError(Exception):
    """Base for errors that must not be turned into partial-success warnings."""


class RecoverableProviderError(ProviderControlError):
    """Transient provider failure; keep checkpoints and continue the same task later."""


class AmbiguousProviderSubmitError(ProviderControlError):
    """Submit may have created a remote job without returning an id; do not auto-resubmit."""
