"""Provider boundary errors that handlers/runtime must interpret."""


class ProviderControlError(Exception):
    """Base for errors that must not be turned into partial-success warnings."""


class ProviderCheckpointError(ProviderControlError):
    """A durable provider checkpoint could not be saved before a safe submit."""


class RecoverableProviderError(ProviderControlError):
    """Transient provider failure; keep checkpoints and continue the same task later."""


class AmbiguousProviderSubmitError(ProviderControlError):
    """Submit may have created a remote job without returning an id; do not auto-resubmit."""

    def __init__(
        self,
        message: str,
        *,
        remote_task_id: str | None = None,
        job_key: str | None = None,
        asset_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.remote_task_id = remote_task_id
        self.job_key = job_key
        self.asset_id = asset_id
