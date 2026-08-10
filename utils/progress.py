from collections.abc import Callable


ProgressCallback = Callable[[str], None]


def emit(on_progress: ProgressCallback | None, message: str) -> None:
    """Send a short progress line to the UI when a callback is provided."""

    if on_progress is not None:
        on_progress(message)
