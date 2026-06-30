from src.api.web.application import create_app


app = create_app()


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("uvicorn is required. Run `pip install -r requirements.txt`.") from exc

    uvicorn.run("src.__main__:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
