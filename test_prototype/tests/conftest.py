import pytest

from core.canonical import load_canonical, mirror_pairs_478
from core.config import check_models, load_config, resolve


@pytest.fixture(scope="session")
def cfg():
    config = load_config()
    if any(v != "OK" for v in check_models(config).values()):
        pytest.skip("Brak modeli — uruchom: uv run python -m core download-models")
    return config


@pytest.fixture(scope="session")
def canonical(cfg):
    return load_canonical(resolve(cfg["models"]["canonical_face"]))


@pytest.fixture(scope="session")
def pairs(canonical):
    return mirror_pairs_478(canonical)
