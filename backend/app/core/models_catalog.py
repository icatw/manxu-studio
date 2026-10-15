"""Canonical model identifiers shared by settings and ORM defaults.

Keep this module free of Settings imports so SQLAlchemy models can use the
defaults without circular imports through ``app.core.config``.
"""

DEFAULT_IMAGE_MODEL = "qwen-image-3.0"
DEFAULT_TEXT_MODEL = "qwen-plus"
