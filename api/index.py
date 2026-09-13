"""Vercel-compatible WSGI entrypoint for Anju AI."""

# Keep the deployment import graph small; main.py is the desktop launcher.
from deployment_app import app

__all__ = ["app"]
