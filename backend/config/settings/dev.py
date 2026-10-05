"""Development settings: DEBUG defaults on, everything else from base."""

from .base import *  # noqa: F403

DEBUG = env("DJANGO_DEBUG", default=True)  # noqa: F405
