from __future__ import annotations

from rmao.config.loader import _normalize_owner, _normalize_repository


def test_github_config_accepts_common_repository_formats() -> None:
    assert _normalize_owner("https://github.com/bablu-builds") == "bablu-builds"
    assert _normalize_repository("https://github.com/bablu-builds/replica-pro.git") == "replica-pro"
    assert _normalize_repository("git@github.com:bablu-builds/replica-pro.git") == "replica-pro"
    assert _normalize_repository("bablu-builds/replica-pro") == "replica-pro"