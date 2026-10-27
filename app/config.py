import os

from app import env  # noqa: F401  (loads .env)


def dsn() -> str:
    # 127.0.0.1, not "localhost": on Windows localhost tries IPv6 first, Docker only publishes
    # the port on IPv4, and every connection waited about two minutes for the IPv6 attempt to fail.
    return (
        f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@127.0.0.1:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )
