from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.understand_reuse import ActorContextFixture, compose_agent_candidate
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.workbench import CatalystWorkbench


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    config_path = Path(sys.argv[1]).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    workspace = Path(config["workspace"])
    roots = [Path(value) for value in config["roots"]]
    wiki = ProjectWiki(
        workspace,
        roots,
        enterprise_id=config["enterprise_id"],
        project_id=config["project_id"],
        backend=config["backend"],
    )
    gateway = CatalystGateway(workspace)
    workbench = CatalystWorkbench(workspace, roots)
    raw_actor = config["actor"]
    actor = ActorContextFixture(
        actor_id=raw_actor["actor_id"],
        enterprise_id=raw_actor["enterprise_id"],
        project_id=raw_actor["project_id"],
        department_ids=tuple(raw_actor["department_ids"]),
        active_department_id=raw_actor["active_department_id"],
        department_labels=raw_actor["department_labels"],
        readable_scope_ids=tuple(raw_actor["readable_scope_ids"]),
        permissions=frozenset(raw_actor["permissions"]),
        verified=bool(raw_actor["verified"]),
        simulation=bool(raw_actor["simulation"]),
    )
    result = compose_agent_candidate(
        request=config["request"],
        actor=actor,
        wiki=wiki,
        gateway=gateway,
        capability_catalog=workbench._catalog,
    )
    print(json.dumps({"pid": os.getpid(), **result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
