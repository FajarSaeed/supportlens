"""
Convenience entry point — run the SupportLens backend with:

    python backend/run.py

from the repo root, or:

    python run.py

from inside the backend/ directory.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
