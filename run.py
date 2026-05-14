"""
run.py
Starts PaySnap — FastAPI backend + React frontend

Usage:
    python run.py

Backend:  http://localhost:8000
Frontend: http://localhost:5173
API docs: http://localhost:8000/docs
"""

import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")


def check_requirements():
    """Check everything is installed before starting."""
    import shutil

    issues = []

    if not shutil.which("uvicorn"):
        issues.append("uvicorn not installed — run: pip install uvicorn fastapi")

    if not os.path.exists(os.path.join(FRONTEND, "node_modules")):
        issues.append("Node modules missing — run: cd frontend && npm install")

    if not os.path.exists(os.path.join(ROOT, "data", "labor_law.db")):
        issues.append("Database missing — run: python data/build_db.py")

    if issues:
        print("\n⚠️  Setup incomplete:")
        for issue in issues:
            print(f"   → {issue}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    check_requirements()

    print("\n" + "="*45)
    print("  💼 PaySnap")
    print("  Tu recibo. Tu derecho. En tu teléfono.")
    print("="*45)
    print(f"\n  Backend:  http://localhost:8000")
    print(f"  Frontend: http://localhost:5173")
    print(f"  API docs: http://localhost:8000/docs")
    print(f"\n  Press Ctrl+C to stop")
    print("="*45 + "\n")

    # Start FastAPI backend
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--reload", "--port", "8000", "--host", "0.0.0.0"],
        cwd=ROOT
    )

    # Start React frontend
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND
    )

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\nStopping PaySnap...")
        backend.terminate()
        frontend.terminate()
        print("Done.")