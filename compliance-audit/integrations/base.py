"""Abstract base for compliance tool integrations.

## Writing a new integration

Subclass ``ComplianceIntegration`` and implement two methods:

### ``get_framework_controls(framework_id) -> list[Control]``

Return every control that belongs to the given framework. Each ``Control``
must carry:

- ``id`` - the tool's internal identifier, used only within the same integration
- ``external_id`` - the human-readable control code (e.g. ``"AM-01"``)
- ``name`` - full display name (e.g. ``"AM-01 Inventory of assets"``)

### ``get_control_documentation(control, docs_dir) -> list[ControlDocumentationRow]``

Fetch and materialise all evidence / documentation for a single control.
The implementation is fully responsible for:

- Deciding what counts as a document for this control
- Downloading file content and writing it under ``docs_dir``
- Populating each ``ControlDocumentationRow`` field:

  - ``family``: control family prefix, e.g. ``"AM"`` from ``"AM-01"``
  - ``control``: the human-readable control code, e.g. ``"AM-01"``
  - ``source_type``: one of ``"local_file"`` | ``"confluence"`` |
    ``"external_url"`` (or any string meaningful to the auditor)
  - ``link``: absolute file path when ``source_type="local_file"``,
    otherwise the original URL
  - ``status``: ``"ready"`` if content is locally available,
    ``"needs_manual_fetch"`` if a human must retrieve it
  - ``doc_type``: ``DocumentType.EVIDENCE``, ``DocumentType.DOCUMENTATION``,
    or ``DocumentType.NONE`` when the distinction is unknown

The bootstrap pipeline deduplicates rows by ``(family, control, link)``
across runs, so the integration does not need to worry about idempotency
at the row level.

### Suggested file layout under ``docs_dir``

    docs/<family>/<safe-filename>.txt

where ``family`` is the control family prefix (``"AM"``, ``"IDM"``, …).

### Registering the integration

Add an ``elif`` branch in ``bootstrap.build_client`` that reads the
required credentials from environment variables and returns an instance
of the new class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DocumentType(Enum):
    EVIDENCE = "evidence"
    DOCUMENTATION = "documentation"
    NONE = "none"


@dataclass
class Control:
    id: str
    external_id: str
    name: str


@dataclass
class ControlDocumentationRow:
    family: str
    control: str
    source_type: str
    link: str
    status: str
    doc_type: DocumentType = DocumentType.NONE


class ComplianceIntegration(ABC):
    @abstractmethod
    def get_framework_controls(self, framework_id: str) -> list[Control]:
        """Return all controls for the given framework."""

    @abstractmethod
    def get_control_documentation(self, control: Control, docs_dir: Path) -> list[ControlDocumentationRow]:
        """Fetch and save all documentation / evidence for a single control.

        The implementation decides how to retrieve documents, whether to
        download files or record URLs, and what ``source_type`` / ``status``
        to assign.  Files should be written under ``docs_dir``.
        """
