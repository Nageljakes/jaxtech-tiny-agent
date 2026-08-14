"""Versioned Jaxtech capability catalogue and deterministic mapping guardrails."""

import json
import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.schemas import MappingResult

CATALOG_VERSION = "2026-08-14"
CATALOG_PATH = Path(__file__).resolve().parents[1] / "catalog" / "capabilities.v1.json"

# Human vocabulary that does not naturally overlap terse skill IDs.
ALIASES: dict[str, set[str]] = {
    "smart-home-iot-integration": {
        "home", "lights", "lighting", "camera", "cameras", "inverter",
        "sensor", "sensors", "security", "geyser", "mqtt", "automation",
    },
    "xlsx": {"excel", "spreadsheet", "workbook", "csv", "rows", "columns"},
    "google-workspace": {"gmail", "calendar", "google", "drive", "sheets", "docs"},
    "himalaya": {"email", "imap", "smtp", "mailbox"},
    "agentmail": {"email", "inbox", "mail"},
    "airtable": {"airtable", "records", "database"},
    "telephony": {"phone", "sms", "whatsapp", "twilio", "call", "calls"},
    "openhue": {"hue", "philips", "lights", "lighting"},
}


class Capability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: str


class CapabilityCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    source_repository: str
    source_commit: str
    count: int
    capabilities: list[Capability]


@lru_cache(maxsize=1)
def load_catalog() -> CapabilityCatalog:
    catalog = CapabilityCatalog.model_validate_json(CATALOG_PATH.read_text())
    if catalog.version != CATALOG_VERSION:
        raise ValueError("Capability catalogue version mismatch")
    if catalog.count != len(catalog.capabilities):
        raise ValueError("Capability catalogue count mismatch")
    if len({item.id for item in catalog.capabilities}) != catalog.count:
        raise ValueError("Capability catalogue contains duplicate IDs")
    return catalog


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def candidate_capabilities(query: str, *, limit: int = 12) -> list[Capability]:
    """Return lexical candidates before Gemini reasons about fit."""
    if limit < 1:
        raise ValueError("limit must be positive")
    query_tokens = _tokens(query)
    ranked: list[tuple[int, str, Capability]] = []
    for item in load_catalog().capabilities:
        searchable = _tokens(f"{item.id} {item.name} {item.category}")
        searchable.update(ALIASES.get(item.id, set()))
        score = len(query_tokens & searchable)
        if score:
            ranked.append((score, item.id, item))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in ranked[:limit]]


def validate_mapping(mapping: MappingResult) -> MappingResult:
    """Fail closed when model output cites a capability absent from the snapshot."""
    known = {item.id for item in load_catalog().capabilities}
    unknown = sorted({match.capability_id for match in mapping.matches} - known)
    if unknown:
        raise ValueError(f"Unknown capability ID(s): {', '.join(unknown)}")
    return mapping
