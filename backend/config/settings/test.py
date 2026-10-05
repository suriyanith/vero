"""Test settings: fast hashing, synchronous tasks, no live LLM — ever."""

from .base import *  # noqa: F403

DEBUG = False

# MD5 is insecure but fine for throwaway test users, and much faster.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Tasks run inline so tests see their effects immediately.
TASKS = {
    "default": {
        "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
    },
}

# Automated tests never call the real Gemini API.
VERO_LLM_MODE = "fake"
