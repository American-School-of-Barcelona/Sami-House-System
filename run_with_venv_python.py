"""
This script runs app.py using the venv's Python interpreter
Run this with: python run_with_venv_python.py
"""
import subprocess
import sys
import os

# Get the path to the venv Python
venv_python = os.path.join('venv', 'Scripts', 'python.exe')

if not os.path.exists(venv_python):
    print(f"ERROR: Virtual environment Python not found at {venv_python}")
    print("Please create a virtual environment first with: python -m venv venv")
    sys.exit(1)

print(f"Using Python from venv: {venv_python}")
print("-" * 60)

# Run app.py with the venv Python
subprocess.run([venv_python, 'app.py'])
