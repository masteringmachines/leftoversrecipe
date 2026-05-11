# 🍳 Pantry & Pot — Recipe Finder

A lightweight semantic recipe search engine using **Vector DB principles** — built with TF-IDF embeddings and cosine similarity. No cloud APIs, no external ML services, runs entirely offline.

---

## Architecture

```
recipe_finder/
├── core/
│   ├── vector_store.py    # Vector DB: TF-IDF embeddings + cosine similarity
│   └── data_loader.py     # Recipe ingestion & dataset management
├── templates/
│   └── index.html         # Web UI (pure HTML/CSS/JS)
├── data/                  # Generated index lives here (auto-created)
├── app.py                 # Flask REST API
├── cli.py                 # Command-line interface
└── requirements.txt
```

### Vector DB Design

| Concern | Implementation |
|---|---|
| **Embeddings** | TF-IDF with bigrams (`ngram_range=(1,2)`) |
| **Similarity** | Cosine similarity via `sklearn` |
| **Storage** | In-memory sparse matrix + `pickle` for persistence |
| **Indexing** | Document = title×2 + ingredients×2 + instructions[:200] |
| **Filtering** | Metadata pre-filter (cuisine, prep_time) before vector search |
| **Missing ingredients** | Fuzzy substring match against user's pantry |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Build the index

```bash
# Build from built-in 500-recipe dataset (instant)
python cli.py build

# Or build with more recipes
python cli.py build --count 1000

# Or load your own JSON file (see format below)
python cli.py build --json my_recipes.json
```

### 3. Search from the terminal

```bash
python cli.py search "chicken, garlic, soy sauce, honey"

# With filters
python cli.py search "pasta, garlic" --cuisine Italian --max-time 30

# More results
python cli.py search "eggs, flour, butter" --top 8
```

### 4. Launch the web UI

```bash
python cli.py serve
# → http://localhost:5000
```

---

## CLI Reference

```
python cli.py build [--json PATH] [--count N]
python cli.py search INGREDIENTS [--top N] [--cuisine NAME] [--max-time MINS]
python cli.py serve [--port N] [--debug]
```

---

## Using Your Own Recipes

The loader accepts a JSON array of recipe objects. Supported fields:

```json
[
  {
    "title": "Honey Garlic Chicken",
    "ingredients": ["chicken", "garlic", "honey", "soy sauce"],
    "instructions": "Mix sauce. Cook chicken. Glaze.",
    "cuisine": "Asian",
    "prep_time": 30,
    "url": "https://example.com/recipe"
  }
]
```

Loads up to **10,000 recipes** from a JSON file.

---

## Web API

| Endpoint | Description |
|---|---|
| `GET /api/search?q=chicken,garlic` | Search recipes |
| `GET /api/search?q=pasta&cuisine=Italian&max_time=30&top_k=5` | Filtered search |
| `GET /api/meta` | Index stats + available cuisines |

### Search response

```json
{
  "query": "chicken, garlic, soy sauce",
  "total": 5,
  "results": [
    {
      "rank": 1,
      "score": 0.6241,
      "title": "Honey Garlic Soy Glazed Chicken",
      "cuisine": "Asian",
      "prep_time": 45,
      "ingredients": ["chicken thighs", "garlic", "soy sauce", "honey"],
      "instructions": "Mix soy sauce, honey...",
      "missing_ingredients": ["sesame oil", "green onions"],
      "source_url": ""
    }
  ]
}
```

---

## Design Principles

- **Single responsibility**: `vector_store.py` is pure DB logic; `data_loader.py` is pure ETL; `app.py` is pure routing.
- **No unnecessary dependencies**: Uses only `scikit-learn`, `numpy`, `flask`, `click` — all battle-tested.
- **Lightweight persistence**: A 500-recipe index is ~200KB on disk.
- **Offline-first**: Zero network calls at search time.
- **Extensible**: Swap TF-IDF for a real embedding model by subclassing `RecipeVectorStore`.
