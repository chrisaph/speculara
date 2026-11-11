import pytest


@pytest.fixture(autouse=True)
def clear_local_analysis_cache():
    from app.main import _analysis_cache
    _analysis_cache.clear()
    yield
    _analysis_cache.clear()
