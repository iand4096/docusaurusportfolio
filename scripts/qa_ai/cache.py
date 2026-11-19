"""Cache completed AI checks against the review implementation and inputs."""
import hashlib
from functools import cached_property
from pathlib import Path

import qa_policy
import qa_review_cache
from qa_checks import base, source
from qa_review_cache import ReviewCache, digest

from . import client

AI_REVIEW_POLICY_VERSION = "2026-11-16-substantive-defects-v7"
PACKAGE_DIR = Path(__file__).resolve().parent


class AIReviewCache:
    def __init__(self, directory: Path, *, enabled: bool = True):
        self.cache = ReviewCache(directory, enabled=enabled)

    @cached_property
    def fingerprint(self) -> str:
        files = {f"qa_ai/{path.name}": path for path in PACKAGE_DIR.glob("*.py")}
        files.update({module.__name__: Path(module.__file__)
                      for module in (base, source, qa_policy, qa_review_cache)})
        return digest({name: hashlib.sha256(path.read_bytes()).hexdigest()
                       for name, path in files.items()})

    def run(self, check, sources, scope, compute):
        if check.source != "ai" or not self.cache.enabled:
            return compute()
        return self.cache.run({
            "scope": scope,
            "check": check.name,
            "sources": sources,
            "model": client.MODEL,
            "api_url": client.API_URL,
            "policy": AI_REVIEW_POLICY_VERSION,
            "implementation": self.fingerprint,
            "defects_only": check.defects_only,
        }, compute)
