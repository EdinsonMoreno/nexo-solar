#!/usr/bin/env python
"""Entry point script for SolarSense SCADA application.

This script should be run from the project root directory.
It properly sets up the Python path and launches the application.

Usage:
    python run.py
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the main application
from modbuspython.main_app import main

if __name__ == "__main__":
    sys.exit(main())
