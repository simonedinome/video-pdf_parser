from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(fn: Callable[[], T], max_attempts: int = 3, base_delay: float = 5.0) -> T:
    """Call *fn* up to *max_attempts* times with linear backoff.

    Delays: base_delay * attempt (5s, 10s, 15s for default base_delay=5.0).
    Raises the last exception if all attempts fail.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Tentativo %d/%d fallito: %s: %s",
                attempt,
                max_attempts,
                type(exc).__name__,
                exc,
            )
            if attempt < max_attempts:
                delay = base_delay * attempt
                logger.info("Attesa %.1fs prima del prossimo tentativo...", delay)
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]
