"""Narrow local tools owned by the desktop workspace."""

import os

from agent_runtime.contracts import CapabilityDescriptor, Failure, Success


CATALOG = "list_workspace_tools"
WRITE_NOTE = "write_workspace_note"


class ToolCatalog:
    def __init__(self, available, granted):
        self.available = available
        self.granted = granted

    def describe(self):
        return CapabilityDescriptor(
            id=CATALOG,
            name="List workspace tools",
            description="List mounted tools and which ones are granted for this turn.",
            input_schema={"type": "object", "additionalProperties": False},
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        return Success({"tools": [
            {"id": name, "granted_this_turn": name in self.granted}
            for name in self.available
        ]})


class WriteNote:
    def __init__(self, root, run_id):
        self.root = root
        self.run_id = run_id

    def describe(self):
        return CapabilityDescriptor(
            id=WRITE_NOTE,
            name="Save a workspace note",
            description="Save one Markdown note to the workspace output folder. No path or overwrite is allowed.",
            input_schema={
                "type": "object",
                "properties": {"title": {"type": "string"}, "text": {"type": "string"}},
                "required": ["title", "text"],
                "additionalProperties": False,
            },
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        title, body = parameters["title"].strip(), parameters["text"].strip()
        if not 1 <= len(title) <= 120 or len(title.splitlines()) != 1 or not 1 <= len(body) <= 12000:
            return Failure("A note needs a one-line title and bounded nonempty text.")
        if self.root.resolve() != self.root:
            return Failure("Workspace output directory must not redirect to another location.")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / (self.run_id + ".md")
        if path.exists() or path.is_symlink():
            return Failure("This turn already saved a note.")
        temporary = path.with_suffix(".tmp")
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(f"# {title}\n\n{body}\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        return Success({"artifact_id": self.run_id, "title": title})
