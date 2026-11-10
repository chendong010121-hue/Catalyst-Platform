"""The identity of the code that turns a model answer into a card.

A card records the method package its prompts came from and nothing about the code that
reads the answer. Two live cards of the same deck, taken twenty-two minutes apart,
carried the same method package sha256, the same card sha256, and the same source
manifest — and still came out structurally different: one predates scope-state
inheritance, so it has no `scope_state_inheritance` at all and 17 duplicate-entity
merges where the other has 1 and 3. A fingerprint that cannot tell those two runs apart
cannot support the claim that their scores are comparable, so the code carries its own
digest here and the attribution records it beside the method package.

Only this package's own modules are read. The vendored tree and the config/workspace
directories are not: a dependency bump or a settings file that changes no answered byte
should not read as a new pipeline.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parent


def digest_of(directory: Path) -> str:
    """sha256 over the module names and bytes of one directory, in name order."""
    digest = hashlib.sha256()
    for path in sorted(Path(directory).glob("*.py")):
        if not path.is_file():
            continue
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


@lru_cache(maxsize=1)
def pipeline_sha256() -> str:
    """The digest of the code this process is running.

    Read once: a card names the code that produced it, and the code cannot change under
    a running process. A test that edits a file calls `digest_of` on its own directory
    instead, so the cache never hides a change from it.
    """
    return digest_of(_PACKAGE)
