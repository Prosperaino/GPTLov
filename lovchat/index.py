from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

from .ingest import DocumentChunk


class VectorStore:
    """Wrapper around a TF-IDF matrix and associated metadata."""

    def __init__(self, vectorizer: TfidfVectorizer, matrix, metadata: List[Dict[str, Any]]):
        self.vectorizer = vectorizer
        self.matrix = matrix
        self.metadata = metadata

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "vectorizer": self.vectorizer,
                "matrix": self.matrix,
                "metadata": self.metadata,
            },
            path,
        )

    @classmethod
    def load(cls, path: Path) -> "VectorStore":
        bundle = joblib.load(path)
        return cls(bundle["vectorizer"], bundle["matrix"], bundle["metadata"])  # type: ignore[arg-type]


def build_vector_store(chunks: List[DocumentChunk], workspace_dir: Path, max_features: int | None = 50000) -> Path:
    """Create and persist a vector store from prepared chunks."""

    if not chunks:
        raise ValueError("No document chunks provided. Did you extract the archives?")

    texts = [chunk.text for chunk in chunks]
    metadata = [
        {
            "title": chunk.title,
            "refid": chunk.refid,
            "source_path": str(chunk.source_path),
            "content": chunk.text,
        }
        for chunk in chunks
    ]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        max_features=max_features,
        ngram_range=(1, 2),
    )
    matrix = vectorizer.fit_transform(texts)

    store = VectorStore(vectorizer, matrix, metadata)
    path = workspace_dir / "vector_store.pkl"
    store.save(path)
    return path
