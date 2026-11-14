import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings

def check():
    print("=" * 60)
    print("Field Shift Environment Verification Check")
    print("=" * 60)

    # 1. Python version
    py_ver = sys.version_info
    print(f"Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro} ... {'[OK]' if py_ver >= (3, 10) else '[WARN]'}")

    # 2. Check packages
    required = ["fastapi", "pydantic", "jwt", "psycopg2", "dotenv", "pandas", "numpy", "xarray", "pyarrow", "requests"]
    for pkg in required:
        try:
            __import__(pkg)
            print(f"Package '{pkg}': [OK]")
        except ImportError:
            print(f"Package '{pkg}': [MISSING - run pip install -r requirements.txt]")

    # 3. Check environment settings
    is_postgres_url = settings.database_url.startswith(("postgresql://", "postgres://"))
    print(f"Neon/PostgreSQL URL: {'[CONFIGURED]' if is_postgres_url else '[MISSING - set DATABASE_URL in backend/.env]'}")
    print(f"Clerk secret: {'[CONFIGURED]' if settings.clerk_secret_key else '[MISSING - set CLERK_SECRET_KEY]'}")
    print(f"Clerk issuer: {'[CONFIGURED]' if settings.clerk_issuer else '[MISSING - set CLERK_ISSUER]'}")
    print(f"Clerk JWKS URL: {'[CONFIGURED]' if settings.clerk_jwks_url else '[MISSING - set CLERK_JWKS_URL]'}")

    # 4. Storage directories
    cache_dir = os.getenv("CACHE_DIR", "data/cache")
    os.makedirs(cache_dir, exist_ok=True)
    print(f"Cache Directory '{cache_dir}': [WRITABLE]")

    print("=" * 60)
    print("Verification complete.")

if __name__ == "__main__":
    check()
