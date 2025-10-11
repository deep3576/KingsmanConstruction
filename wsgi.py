import sys
import os

# Ensure project path is on sys.path (adjust if your project folder differs)
project_home = os.path.abspath(os.path.dirname(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application  # PythonAnywhere expects `application`