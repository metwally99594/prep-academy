"""Shared SlowAPI rate limiter instance for the entire app.

All routes that need rate limiting import `limiter` from here.
server.py still owns app.state.limiter + the exception handler.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
