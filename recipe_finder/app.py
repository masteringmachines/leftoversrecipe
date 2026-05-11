"""
Flask web interface for the Recipe Finder.
Thin controller layer — all logic lives in core/.
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from core.vector_store import RecipeVectorStore

INDEX_PATH = Path("data/recipe_index.pkl")

app = Flask(__name__)
store: RecipeVectorStore | None = None


def get_store() -> RecipeVectorStore:
    global store
    if store is None:
        if not INDEX_PATH.exists():
            raise RuntimeError("Index not built. Run: python cli.py build")
        store = RecipeVectorStore.load(INDEX_PATH)
    return store


# ------------------------------------------------------------------ #
#  Routes                                                             #
# ------------------------------------------------------------------ #

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400

    top_k = min(int(request.args.get("top_k", 5)), 20)
    cuisine = request.args.get("cuisine") or None
    max_time = request.args.get("max_time")
    max_time = int(max_time) if max_time else None

    try:
        s = get_store()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    results = s.search(query, top_k=top_k, cuisine_filter=cuisine, max_prep_time=max_time)

    return jsonify({
        "query": query,
        "total": len(results),
        "results": [
            {
                "rank": i + 1,
                "score": round(r.score, 4),
                "title": r.recipe.title,
                "cuisine": r.recipe.cuisine,
                "prep_time": r.recipe.prep_time,
                "ingredients": r.recipe.ingredients,
                "instructions": r.recipe.instructions[:600],
                "missing_ingredients": r.missing,
                "source_url": r.recipe.source_url,
            }
            for i, r in enumerate(results)
        ],
    })


@app.route("/api/meta")
def meta():
    try:
        s = get_store()
        return jsonify({
            "total_recipes": s.count,
            "cuisines": s.cuisines,
        })
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503


if __name__ == "__main__":
    app.run(debug=True, port=5000)
