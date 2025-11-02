#!/usr/bin/env python3
"""Standalone launcher for Elastic RAG Gradio UI.

This script provides a simple way to launch the Gradio web interface
for the Elastic RAG system.

Usage:
    python demos/launch_ui.py
    python demos/launch_ui.py --host 0.0.0.0 --port 7860
    python demos/launch_ui.py --api-url http://localhost:8000 --share
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.gradio_app import launch_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Launch Elastic RAG Gradio UI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="URL of the FastAPI backend",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to bind to",
    )

    parser.add_argument(
        "--share",
        action="store_true",
        help="Enable Gradio public URL sharing",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    logger.info("=" * 60)
    logger.info("Elastic RAG - Gradio UI")
    logger.info("=" * 60)
    logger.info(f"API URL: {args.api_url}")
    logger.info(f"UI Address: http://{args.host}:{args.port}")
    logger.info(f"Share: {args.share}")
    logger.info("=" * 60)

    try:
        launch_app(
            api_url=args.api_url,
            host=args.host,
            port=args.port,
            share=args.share,
        )
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Failed to launch UI: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
