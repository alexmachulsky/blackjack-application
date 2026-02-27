"""
Rate limiter singleton — shared across the application.

Uses slowapi (built on top of limits) to throttle per-IP.
The limiter is attached to `app.state.limiter` in main.py.

In tests the limiter is enabled=False so that rapid test requests
don't trigger 429 responses (see conftest.py).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, enabled=True)
