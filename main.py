import asyncio
from dotenv import load_dotenv

from src.runner import run


def main() -> None:
    load_dotenv()
    try:
        import uvloop  # type: ignore

        uvloop.install()
    except Exception:
        pass
    asyncio.run(run())


if __name__ == "__main__":
    main()
