#!/usr/bin/env python3
"""
Wrapper script to run the database import
Run this from the project root directory
"""

import os
import sys

# Add the src/api directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'api'))

# Import and run the import script
from import_data import main

if __name__ == "__main__":
    main()

