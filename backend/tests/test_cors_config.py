from app.config import cors_origins


def test_netlify_origin_is_allowed_even_with_stale_local_cors_setting():
    assert cors_origins('http://localhost:8443', 'https://speculara.netlify.app') == ['http://localhost:8443', 'https://speculara.netlify.app']


def test_cors_normalizes_copy_pasted_quotes_slashes_and_duplicates():
    assert cors_origins(' "https://speculara.netlify.app/",https://speculara.netlify.app ') == ['https://speculara.netlify.app']


def test_cors_rejects_paths_credentials_wildcards_and_non_http_schemes():
    assert cors_origins('*,https://user:pass@example.com,https://example.com/path,file:///tmp,https://example.com?q=1') == []
