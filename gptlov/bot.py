from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

from .index import VectorStore
from .settings import settings


@dataclass
class RetrievalResult:
    score: float
    content: str
    metadata: Dict[str, Any]


class GPTLovBot:
    """Simple retrieval-augmented chatbot for Lovdata content."""

    def __init__(self, store_path: str | os.PathLike[str], model: str | None = None):
        self.store = VectorStore.load(Path(store_path))
        self.model = model or settings.openai_model
        self._client: OpenAI | None = None

    def _ensure_client(self) -> OpenAI:
        if self._client:
            return self._client

        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Cannot generate model responses.")

        if base_url:
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self._client = OpenAI(api_key=api_key)
        return self._client

    def retrieve(self, question: str, top_k: int | None = None) -> List[RetrievalResult]:
        top_k = top_k or settings.top_k
        query_vector = self.store.vectorizer.transform([question])
        scores = cosine_similarity(self.store.matrix, query_vector).ravel()

        top_indices = np.argsort(scores)[::-1][:top_k]
        results: List[RetrievalResult] = []
        for idx in top_indices:
            metadata = self.store.metadata[idx]
            results.append(
                RetrievalResult(
                    score=float(scores[idx]),
                    content=metadata["content"],
                    metadata={k: v for k, v in metadata.items() if k != "content"},
                )
            )
        return results

    def generate_answer(self, question: str, context_blocks: List[RetrievalResult]) -> str:
        try:
            client = self._ensure_client()
        except RuntimeError as exc:
            context = "\n\n".join(block.content for block in context_blocks)
            return (
                "No OpenAI API key configured. Here are the most relevant excerpts:\n\n"
                f"{context}"
            )

        context_text = "\n\n".join(
            f"Kilde: {block.metadata.get('title') or block.metadata.get('refid') or block.metadata.get('source_path')}\n{block.content}"
            for block in context_blocks
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "Du er GPTLov, en hjelpsom assistent som svarer på spørsmål om norske lover og "
                    "sentrale forskrifter. Oppgi kun informasjon hentet fra konteksten. Hvis svaret "
                    "ikke finnes i utdragene, si at du ikke er sikker."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Kontekst:\n" + context_text + "\n\n" + f"Spørsmål: {question}\n" + "Svar på norsk."
                ),
            },
        ]

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )

        return response.choices[0].message.content.strip()

    def ask(self, question: str, top_k: int | None = None) -> dict[str, Any]:
        context_blocks = self.retrieve(question, top_k=top_k)
        answer = self.generate_answer(question, context_blocks)
        return {
            "answer": answer,
            "contexts": [
                {
                    "score": block.score,
                    **block.metadata,
                    "content": block.content,
                }
                for block in context_blocks
            ],
        }
