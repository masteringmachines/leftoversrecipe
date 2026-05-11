"""
Lightweight Vector Store using TF-IDF embeddings + cosine similarity.
No external ML services required — runs entirely offline.
"""

from __future__ import annotations

import json
import math
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Recipe:
    """Immutable recipe record stored in the vector DB."""

    id: int
    title: str
    ingredients: list[str]
    instructions: str
    cuisine: str = "Unknown"
    prep_time: int = 0  # minutes
    source_url: str = ""

    @property
    def searchable_text(self) -> str:
        """Combined text used for embedding — title + ingredients get extra weight."""
        ingredient_blob = " ".join(self.ingredients)
        return f"{self.title} {self.title} {ingredient_blob} {ingredient_blob} {self.instructions[:200]}"

    def missing_ingredients(self, query_ingredients: list[str]) -> list[str]:
        """Return ingredients in recipe not present in user's pantry."""
        query_set = {i.lower().strip() for i in query_ingredients}
        missing = []
        for ing in self.ingredients:
            ing_lower = ing.lower().strip()
            # Fuzzy partial match: if any query word appears in ingredient
            matched = any(q in ing_lower or ing_lower in q for q in query_set)
            if not matched:
                missing.append(ing)
        return missing


@dataclass
class SearchResult:
    recipe: Recipe
    score: float
    missing: list[str] = field(default_factory=list)


class RecipeVectorStore:
    """
    In-memory vector store with optional disk persistence.

    Architecture:
    - Documents encoded as TF-IDF sparse vectors
    - Similarity via cosine distance
    - Metadata filters applied post-retrieval (pre-filter on index for speed)
    """

    def __init__(self) -> None:
        self._recipes: list[Recipe] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix: np.ndarray | None = None
        self._is_built = False

    # ------------------------------------------------------------------ #
    #  Indexing                                                             #
    # ------------------------------------------------------------------ #

    def add_recipes(self, recipes: list[Recipe]) -> None:
        self._recipes.extend(recipes)
        self._is_built = False  # invalidate index

    def build_index(self) -> None:
        """Fit TF-IDF vectorizer and compute embedding matrix."""
        if not self._recipes:
            raise ValueError("No recipes to index.")

        corpus = [r.searchable_text for r in self._recipes]
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(corpus)
        self._is_built = True
        print(f"  Index built: {len(self._recipes)} recipes, "
              f"{self._matrix.shape[1]:,} features")

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #

    def search(
        self,
        query: str,
        top_k: int = 5,
        cuisine_filter: str | None = None,
        max_prep_time: int | None = None,
    ) -> list[SearchResult]:
        """
        Retrieve top-k recipes closest to query in embedding space.
        Optional metadata filters narrow the candidate set first.
        """
        if not self._is_built:
            raise RuntimeError("Call build_index() before searching.")

        # --- metadata pre-filter ---
        candidates = self._recipes
        candidate_indices = list(range(len(candidates)))

        if cuisine_filter:
            cf = cuisine_filter.lower()
            candidate_indices = [
                i for i in candidate_indices
                if cf in self._recipes[i].cuisine.lower()
            ]
        if max_prep_time is not None:
            candidate_indices = [
                i for i in candidate_indices
                if self._recipes[i].prep_time <= max_prep_time or self._recipes[i].prep_time == 0
            ]

        if not candidate_indices:
            return []

        # --- vector similarity ---
        query_vec = self._vectorizer.transform([query])
        candidate_matrix = self._matrix[candidate_indices]
        scores = cosine_similarity(query_vec, candidate_matrix)[0]

        # rank & slice
        ranked = sorted(
            zip(candidate_indices, scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        query_ingredients = [q.strip() for q in query.split(",")]
        results = []
        for idx, score in ranked:
            recipe = self._recipes[idx]
            missing = recipe.missing_ingredients(query_ingredients)
            results.append(SearchResult(recipe=recipe, score=float(score), missing=missing))

        return results

    # ------------------------------------------------------------------ #
    #  Persistence                                                         #
    # ------------------------------------------------------------------ #

    def save(self, path: Path) -> None:
        payload = {
            "recipes": self._recipes,
            "vectorizer": self._vectorizer,
            "matrix": self._matrix,
        }
        with open(path, "wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        size_kb = path.stat().st_size // 1024
        print(f"  Saved index → {path} ({size_kb} KB)")

    @classmethod
    def load(cls, path: Path) -> "RecipeVectorStore":
        with open(path, "rb") as f:
            payload = pickle.load(f)
        store = cls()
        store._recipes = payload["recipes"]
        store._vectorizer = payload["vectorizer"]
        store._matrix = payload["matrix"]
        store._is_built = True
        print(f"  Loaded {len(store._recipes):,} recipes from {path}")
        return store

    @property
    def count(self) -> int:
        return len(self._recipes)

    @property
    def cuisines(self) -> list[str]:
        seen: set[str] = set()
        result = []
        for r in self._recipes:
            c = r.cuisine
            if c not in seen:
                seen.add(c)
                result.append(c)
        return sorted(result)
