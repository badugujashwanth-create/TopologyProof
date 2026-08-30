"""Bounded read-only repository ingestion primitives."""

from backend.app.ingestion.git_client import GitClient, GitCommandResult, TreeEntry

__all__ = ["GitClient", "GitCommandResult", "TreeEntry"]
