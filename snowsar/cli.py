"""CLI entry point for SnowSAR."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    """SnowSAR command-line interface."""
    parser = argparse.ArgumentParser(
        prog="snowsar",
        description="SnowSAR — SAR-based snow depth retrieval system",
    )
    subparsers = parser.add_subparsers(dest="command")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # download-model command (for Phase 2)
    subparsers.add_parser("download-model", help="Pre-download ML model from registry")

    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn

        uvicorn.run(
            "snowsar.api.app:create_app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            factory=True,
        )
    elif args.command == "download-model":
        print("Model download not yet implemented (Phase 2)")
    else:
        parser.print_help()
        sys.exit(1)
