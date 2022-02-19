"""Helper file for making generated modules accessible."""
import os
import sys

# Adds this directory to the Python path. Then, the generated files can be found.
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
