import pytest

from app.catalog import (
    CATALOG_VERSION,
    candidate_capabilities,
    load_catalog,
    validate_mapping,
)
from app.schemas import CapabilityMatch, MappingResult


def test_versioned_catalog_contains_all_197_unique_capabilities() -> None:
    catalog = load_catalog()

    assert CATALOG_VERSION == "2026-08-14"
    assert catalog.count == 197
    assert len(catalog.capabilities) == 197
    assert len({item.id for item in catalog.capabilities}) == 197


def test_candidate_selection_finds_smart_home_without_model_guessing() -> None:
    candidates = candidate_capabilities(
        "Coordinate home lights, cameras, inverter and security sensors",
        limit=5,
    )

    assert "smart-home-iot-integration" in [item.id for item in candidates]


def test_candidate_selection_finds_concrete_document_integration() -> None:
    candidates = candidate_capabilities(
        "Put form submissions into an Excel spreadsheet",
        limit=10,
    )

    assert "xlsx" in [item.id for item in candidates]


def test_mapping_validator_accepts_catalog_backed_matches() -> None:
    mapping = MappingResult(
        matches=[
            CapabilityMatch(
                capability_id="smart-home-iot-integration",
                integrations=["Home Assistant", "MQTT"],
                rationale="Coordinates synthetic smart-home devices locally.",
            )
        ],
        unmapped_requirements=["Specific inverter vendor API is unknown"],
    )

    assert validate_mapping(mapping) is mapping


def test_mapping_validator_rejects_invented_capability_ids() -> None:
    mapping = MappingResult(
        matches=[
            CapabilityMatch(
                capability_id="imaginary-everything-connector",
                integrations=["Imaginary API"],
                rationale="This capability does not exist.",
            )
        ],
        unmapped_requirements=[],
    )

    with pytest.raises(ValueError, match="Unknown capability"):
        validate_mapping(mapping)
