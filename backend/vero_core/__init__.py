"""Vero's framework-free coding pipeline.

This package must never import Django (enforced by a test). It takes plain
inputs, talks to the outside world only through the interfaces it defines,
and returns Pydantic models.
"""
