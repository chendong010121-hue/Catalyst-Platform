"""Default context plug-in: recent turns plus traceable, extractive checkpoints."""

from dataclasses import replace

from agent_runtime.contracts import Message

from .context import SERVICE, Projection, apply_projection, estimate
from .plugin_composition import PluginDefinition, PluginEffect


class BudgetedHistory:
    version = "budgeted-extractive/1.0.0"

    def project(self, request, turns, budget):
        plan = Projection(tool_prefixes=tuple(
            (message.tool_call_id, 1600) for message in request.messages
            if message.role == "tool" and len(message.content) > 1600
        ))

        def fits(candidate, limit=budget):
            return estimate(apply_projection(request, candidate)) <= limit

        def add_recent(current, turn):
            return replace(
                current,
                history=(Message("user", turn.question), Message("assistant", turn.answer), *current.history),
                recent_ids=(turn.run_id, *current.recent_ids),
            )

        # Use a contiguous suffix, preserving exact role and order.
        recent = plan
        for turn in reversed(turns):
            candidate = add_recent(recent, turn)
            if not fits(candidate):
                break
            recent = candidate
        else:
            return recent

        # Reserve a modest part of remaining input for source-linked excerpts
        # only when some complete earlier turns would otherwise disappear.
        room = max(0, budget - estimate(apply_projection(request, plan)))
        checkpoint_budget = min(room // 4, 1800)
        with_checkpoint = plan
        for turn in reversed(turns):
            candidate = add_recent(with_checkpoint, turn)
            if not fits(candidate, budget - checkpoint_budget):
                break
            with_checkpoint = candidate
        older = turns[:len(turns) - len(with_checkpoint.recent_ids)]
        excerpts, ids = [], []
        result = recent
        for turn in reversed(older[-6:]):
            excerpt = f"[{turn.run_id}] User: {turn.question[:96]} | Assistant: {turn.answer[:96]}"
            note = "Earlier chat excerpts (incomplete conversation data):\n" + "\n".join([excerpt, *excerpts])
            candidate = replace(
                with_checkpoint, history=(Message("user", note), *with_checkpoint.history),
                checkpoint_ids=(turn.run_id, *ids),
            )
            if not fits(candidate):
                break
            excerpts.insert(0, excerpt)
            ids.insert(0, turn.run_id)
            result = candidate
        return result


def definition():
    return PluginDefinition(
        plugin_id="context-window", version="1.0.0", provides=(SERVICE,), requires=(),
        apply=lambda context: PluginEffect(services={SERVICE: BudgetedHistory()}),
    )
