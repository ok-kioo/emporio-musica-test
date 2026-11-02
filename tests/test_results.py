import pytest

from src.domain import EvidenceBundle, Source, ToolResult, ToolStatus


def test_tool_result_has_explicit_empty_success_envelope() -> None:
    result = ToolResult(status=ToolStatus.SUCCESS)

    assert result.data is None
    assert result.sources == ()
    assert result.message is None


def test_evidence_bundle_retains_auditable_source() -> None:
    source = Source(source="products.csv", record_id=10)
    bundle = EvidenceBundle(
        intent="data",
        access_level=0,
        facts={"product_name": "Violão"},
        sources=(source,),
    )

    assert bundle.sources[0].source == "products.csv"


def test_invalid_access_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="access_level"):
        EvidenceBundle(intent="data", access_level=3)
