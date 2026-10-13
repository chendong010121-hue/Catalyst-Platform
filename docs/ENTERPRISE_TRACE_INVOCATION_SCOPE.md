# Enterprise trace invocation scope

`execute_with_enterprise_identity` returns only the events emitted by the
current invocation. Reusing an adapter for sequential invocations preserves
its full generic trace history, while each returned projection receives only
the current invocation's optional enterprise identity. Multiple invocations
may share a trace ID without inheriting each other's identity.

This is attribution, not authentication or authorization. The helper does not
make the reference adapter safe for concurrent execution.

The defect was reproduced on `36b18a9fe24fe6fbcfe6a5594af63e1d8ee5fc86`:
a second invocation under organization B returned earlier organization A
events attributed to B. ER-6 and ER-7 cover sequential identity changes and
identity-free invocations. Existing conflict rejection remains unchanged.

The selected change repairs the Enterprise projection boundary. Recreating
the adapter for each call would leave the helper defective; replacing trace
infrastructure would add unnecessary coupling. Runtime and Standard contracts
remain unchanged. Rollback is a revert of this candidate commit; merge and
Product acceptance remain owner decisions.
