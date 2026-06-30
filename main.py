from src.__main__ import app


if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn is not installed. Run `pip install -r requirements.txt` before starting the API."
        ) from exc

    uvicorn.run(app, host="0.0.0.0", port=8000)
