"""Enterprise Extension Pilot v0.1 — reference enterprise identity vertical slice.

Uses the unified reference Enterprise Extension path
(`execute_with_enterprise_identity`): validate -> parse identity -> generic
RuntimeAdapter.execute -> attribute trace. No Core / Runtime change. Runs two
enterprise contexts (Org A / Org B) to show portability.
"""

from __future__ import annotations

from enterprise_extensions.identity import (
    EnterpriseIdentity,
    execute_with_enterprise_identity,
)

from .platform_standard_reference import make_stack


def _run_case(identity: EnterpriseIdentity, *, invocation_id: str, trace_id: str):
    registry, adapter = make_stack()
    extensions = dict(identity.to_extension())
    invocation = _identity_invocation(identity, invocation_id=invocation_id, trace_id=trace_id)
    result, events = execute_with_enterprise_identity(adapter, invocation)
    assert result.status == "success"
    assert len(result.artifacts) == 1
    assert all("enterprise.identity" in e.extensions for e in events)

    print(f"--- {identity.organization_id}/{identity.user_id} ---")
    print(f"result.status : {result.status}")
    for e in events:
        ident = e.extensions["enterprise.identity"]["payload"]
        print(f"trace {e.event_type}: org={ident['organization_id']} user={ident['user_id']} "
              f"project={ident.get('project_id')}")
    return result, events


def _identity_invocation(identity: EnterpriseIdentity, *, invocation_id: str, trace_id: str):
    from platform_standard.models import Invocation

    extensions = dict(identity.to_extension())
    return Invocation(
        id=invocation_id,
        capability_id="compose_report",
        capability_version="1.0.0",
        input={"title": f"Report for {identity.organization_id}", "sections": ["Section one."]},
        context={"extensions": {}},
        extensions=extensions,
        trace_id=trace_id,
    )


def main() -> None:
    org_a = EnterpriseIdentity(organization_id="org_alpha", user_id="user_001", project_id="project_a")
    org_b = EnterpriseIdentity(organization_id="org_beta", user_id="user_927", project_id="project_z")

    result_a, _ = _run_case(org_a, invocation_id="inv_org_a", trace_id="trace_org_a")
    result_b, _ = _run_case(org_b, invocation_id="inv_org_b", trace_id="trace_org_b")

    assert result_a.status == "success"
    assert result_b.status == "success"
    assert result_a.output["report_text"].startswith("# Report for org_alpha")
    assert result_b.output["report_text"].startswith("# Report for org_beta")

    print("\nENTERPRISE IDENTITY VERTICAL SLICE PASS (Org A + Org B)")


if __name__ == "__main__":
    main()
