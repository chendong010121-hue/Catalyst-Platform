from __future__ import annotations

from .credentials import setup_user_local_credential


def main() -> int:
    setup_user_local_credential("deepseek.default")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
