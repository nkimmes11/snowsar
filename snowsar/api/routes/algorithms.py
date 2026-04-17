"""Algorithm listing endpoints."""

from fastapi import APIRouter

from snowsar.algorithms.registry import list_algorithms

router = APIRouter()


@router.get("/algorithms")
def get_algorithms() -> list[dict[str, str]]:
    """List available retrieval algorithms with metadata."""
    return list_algorithms()
