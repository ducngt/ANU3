from pathlib import Path


def test_capability_contract_does_not_define_authority_primitive():
    text = Path("src/anu_kernel/capability_contracts.py").read_text(encoding="utf-8")
    assert "authority:" not in text
    assert "authority_ref:" not in text


def test_object_store_provider_logic_is_behind_adapter_boundary():
    service = Path("src/anu_kernel/ingestion_services.py").read_text(encoding="utf-8")
    adapter = Path("src/anu_kernel/object_store.py").read_text(encoding="utf-8")
    assert "FileSystemObjectStore" in service
    assert "urn:anu:adapter:object-store:filesystem" in adapter


def test_retrieval_hit_contract_exposes_source_and_provenance():
    text = Path("src/anu_kernel/ingestion_contracts.py").read_text(encoding="utf-8")
    assert "source_refs" in text
    assert "provenance_ref" in text


def test_no_multimodal_file_is_promoted_to_fact_by_extractor():
    text = Path("src/anu_kernel/media_extractors.py").read_text(encoding="utf-8")
    assert "EpistemicType.FACT" not in text
    assert "ValidationState.APPROVED" not in text
