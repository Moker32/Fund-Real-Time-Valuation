#!/usr/bin/env python3
"""Fund Real-Time Valuation TUI Application"""

import sys
from pathlib import Path

# Add src to path (relative to this script)
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

from ui.app import FundTUIApp


def main():
    """Main entry point."""
    app = FundTUIApp()
    app.run()


if __name__ == "__main__":
    main()
