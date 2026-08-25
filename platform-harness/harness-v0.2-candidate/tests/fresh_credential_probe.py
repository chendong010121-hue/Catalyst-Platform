from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
for path in (ROOT, REPOSITORY_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from harness import CredentialResolver, ProcessEnvironmentCredentialSource, UserLocalCredentialSource  # noqa: E402


def main() -> int:
    store = Path(sys.argv[1])
    resolver = CredentialResolver(
        sources=(
            ProcessEnvironmentCredentialSource(),
            UserLocalCredentialSource(path=store),
        )
    )
    resolution = resolver.resolve("deepseek.default")
    print(
        json.dumps(
            {
                "fresh_process": True,
                "process_env_deepseek_api_key": bool(os.environ.get("DEEPSEEK_API_KEY")),
                "credential_ref": resolution.credential_ref,
                "credential_source_type": resolution.source_type.value,
                "credential_resolved": bool(resolution.value),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
