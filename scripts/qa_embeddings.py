"""Local complaint embeddings. Render paths read cached vectors, never load a model."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import qa_feedback as feedback

MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
REVISION = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
CACHE = Path('.qa/feedback-index/embeddings.json')
DIMENSIONS = 384


def complaint(issue):
    return feedback.normalise(issue.get('message')) + '\nSuggested correction: ' + feedback.normalise(issue.get('suggestion'))


def vector_key(text):
    return hashlib.sha256((MODEL + '@' + REVISION + '\0' + text).encode()).hexdigest()


class ComplaintIndex:
    def __init__(self, *, cache_path=CACHE):
        self.path = cache_path
        try:
            self.cache = json.loads(cache_path.read_text())
            if self.cache.get('model') != MODEL or self.cache.get('revision') != REVISION:
                raise ValueError('Different embedding model')
            if not isinstance(self.cache.get('vectors'), dict):
                raise ValueError('Invalid vectors')
        except (ValueError, OSError, AttributeError):
            self.cache = {'model': MODEL, 'revision': REVISION, 'vectors': {}}

    def populate(self, issues):
        """Explicit comparison path only; no credentials or remote model code needed."""
        import numpy as np
        from sentence_transformers import SentenceTransformer
        texts = sorted({complaint(issue) for issue in issues})
        missing = [text for text in texts if self.vector(text) is None]
        if not missing:
            return
        model = SentenceTransformer(MODEL, revision=REVISION, device='cpu',
            cache_folder=str(self.path.parent / 'models'), trust_remote_code=False,
            model_kwargs={'use_safetensors': True})
        vectors = model.encode(missing, normalize_embeddings=True, convert_to_numpy=True,
                               show_progress_bar=False)
        for text, vector in zip(missing, vectors):
            if vector.shape != (DIMENSIONS,) or not np.isfinite(vector).all():
                raise ValueError('Invalid complaint embedding')
            self.cache['vectors'][vector_key(text)] = vector.tolist()
        feedback.write_atomic(self.path, self.cache)

    def vector(self, text):
        # Pure Python validation lets render-only refreshes work without ML dependencies.
        import math
        vector = self.cache['vectors'].get(vector_key(text))
        if (not isinstance(vector, list) or len(vector) != DIMENSIONS or
                any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector)):
            return None
        norm = sum(v * v for v in vector) ** 0.5
        if not 0.99 <= norm <= 1.01:
            return None
        return vector

    def similarity(self, left, right):
        a, b = self.vector(complaint(left)), self.vector(complaint(right))
        if a is None or b is None:
            return None
        return max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))
