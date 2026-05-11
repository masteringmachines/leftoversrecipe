#!/usr/bin/env python3
"""
CLI for Recipe Finder Vector DB.

Usage:
  python cli.py build              # Build index from built-in data
  python cli.py build --json recipes.json  # Build from custom JSON
  python cli.py search "chicken, garlic, soy sauce"
  python cli.py search "tomato, pasta" --cuisine Italian --max-time 30
  python cli.py serve              # Launch web UI
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

DATA_DIR = Path("data")
INDEX_PATH = DATA_DIR / "recipe_index.pkl"


# ------------------------------------------------------------------ #
#  CLI commands                                                        #
# ------------------------------------------------------------------ #

@click.group()
def cli():
    """🍳 Recipe Finder — semantic search for your leftover ingredients."""


@cli.command()
@click.option("--json", "json_path", default=None, type=click.Path(exists=True),
              help="Path to custom JSON recipe file.")
@click.option("--count", default=500, show_default=True,
              help="Number of recipes to load from built-in dataset.")
def build(json_path: str | None, count: int):
    """Build the vector index from recipe data."""
    from core.data_loader import load_recipes_from_builtin, load_recipes_from_json
    from core.vector_store import RecipeVectorStore

    DATA_DIR.mkdir(exist_ok=True)
    click.echo("⚙  Loading recipes...")

    if json_path:
        recipes = load_recipes_from_json(Path(json_path))
        click.echo(f"  Loaded {len(recipes):,} recipes from {json_path}")
    else:
        recipes = load_recipes_from_builtin(count)
        click.echo(f"  Loaded {len(recipes):,} recipes from built-in dataset")

    click.echo("⚙  Building vector index...")
    store = RecipeVectorStore()
    store.add_recipes(recipes)
    store.build_index()
    store.save(INDEX_PATH)
    click.echo(f"✅ Index ready at {INDEX_PATH}")


@cli.command()
@click.argument("ingredients")
@click.option("--top", default=5, show_default=True, help="Number of results.")
@click.option("--cuisine", default=None, help="Filter by cuisine (e.g. Italian, Asian).")
@click.option("--max-time", default=None, type=int, help="Max prep time in minutes.")
def search(ingredients: str, top: int, cuisine: str | None, max_time: int | None):
    """Search recipes by ingredients. E.g.: python cli.py search "chicken, garlic, honey" """
    from core.vector_store import RecipeVectorStore

    if not INDEX_PATH.exists():
        click.echo("❌ Index not found. Run: python cli.py build", err=True)
        sys.exit(1)

    store = RecipeVectorStore.load(INDEX_PATH)
    results = store.search(ingredients, top_k=top, cuisine_filter=cuisine, max_prep_time=max_time)

    if not results:
        click.echo("No results found. Try different ingredients or remove filters.")
        return

    click.echo(f"\n🔍 Results for: {ingredients}")
    if cuisine:
        click.echo(f"   Cuisine filter: {cuisine}")
    if max_time:
        click.echo(f"   Max prep time: {max_time}m")
    click.echo()

    for r in results:
        bar = "█" * int(r.score * 20)
        click.echo(f"  {'─'*60}")
        click.echo(f"  #{r.recipe.id:04d} {r.recipe.title}")
        click.echo(f"  Score: {r.score:.3f} {bar}")
        click.echo(f"  Cuisine: {r.recipe.cuisine} | Prep: {r.recipe.prep_time}m")
        click.echo(f"  Ingredients: {', '.join(r.recipe.ingredients[:6])}{'...' if len(r.recipe.ingredients) > 6 else ''}")
        if r.missing:
            click.echo(f"  Missing: {', '.join(r.missing[:4])}{'...' if len(r.missing) > 4 else ''}")
        click.echo(f"  Instructions: {r.recipe.instructions[:120]}...")
        if r.recipe.source_url:
            click.echo(f"  🔗 {r.recipe.source_url}")
        click.echo()


@cli.command()
@click.option("--port", default=5000, show_default=True)
@click.option("--debug/--no-debug", default=False)
def serve(port: int, debug: bool):
    """Launch the web UI."""
    from app import app
    click.echo(f"🌐 Starting web UI at http://localhost:{port}")
    app.run(port=port, debug=debug)


if __name__ == "__main__":
    cli()
