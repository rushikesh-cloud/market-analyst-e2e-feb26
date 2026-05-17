from market_analyst.providers.document_intelligence import (
    resolve_document_intelligence_connection_verify,
)


def test_resolve_document_intelligence_connection_verify_defaults_to_none() -> None:
    assert resolve_document_intelligence_connection_verify("") is None
    assert resolve_document_intelligence_connection_verify("   ") is None


def test_resolve_document_intelligence_connection_verify_supports_booleans() -> None:
    assert resolve_document_intelligence_connection_verify("false") is False
    assert resolve_document_intelligence_connection_verify("TRUE") is True


def test_resolve_document_intelligence_connection_verify_supports_ca_bundle_paths() -> None:
    path = r"C:\certs\corp-ca.pem"
    assert resolve_document_intelligence_connection_verify(path) == path
