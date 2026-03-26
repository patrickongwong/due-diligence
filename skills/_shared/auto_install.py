"""Auto-install missing dependencies at runtime."""
import subprocess
import sys


def ensure_installed(*packages):
    """Check for missing packages and pip-install them if needed."""
    missing = []
    for pkg in packages:
        # Handle "pkg>=version" format — import name is before any operator
        import_name = pkg.split(">=")[0].split("==")[0].split("<")[0].strip()
        # Map pip names to import names where they differ
        import_map = {
            "reportlab": "reportlab",
            "matplotlib": "matplotlib",
            "yfinance": "yfinance",
            "edgartools": "edgar",
            "weasyprint": "weasyprint",
        }
        try_name = import_map.get(import_name, import_name)
        try:
            __import__(try_name)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing],
            stdout=subprocess.DEVNULL,
        )
