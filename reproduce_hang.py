import time
import sys
import os

print("Starting import test...")
start = time.time()
try:
    import app.main
    print(f"Import successful in {time.time() - start:.2f} seconds")
except Exception as e:
    print(f"Import failed: {e}")
