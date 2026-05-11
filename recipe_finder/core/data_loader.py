"""
Data ingestion: downloads the RecipeNLG / RecipeBox sample dataset,
parses it, and loads it into the vector store.
"""

from __future__ import annotations

import csv
import io
import json
import random
import re
import zipfile
from pathlib import Path
from typing import Iterator

from core.vector_store import Recipe

# ------------------------------------------------------------------ #
#  Built-in sample data (used when download is unavailable)           #
# ------------------------------------------------------------------ #

SAMPLE_RECIPES = [
    {
        "title": "Honey Garlic Soy Glazed Chicken",
        "ingredients": ["chicken thighs", "garlic", "soy sauce", "honey", "sesame oil", "ginger", "green onions"],
        "instructions": "Mix soy sauce, honey, minced garlic, and ginger. Marinate chicken for 30 min. Pan-fry until golden, baste with glaze repeatedly until caramelized. Garnish with green onions.",
        "cuisine": "Asian",
        "prep_time": 45,
    },
    {
        "title": "Garlic Butter Pasta",
        "ingredients": ["pasta", "garlic", "butter", "parmesan", "parsley", "salt", "pepper"],
        "instructions": "Boil pasta al dente. Sauté garlic in butter until fragrant. Toss pasta with garlic butter, parmesan, and parsley.",
        "cuisine": "Italian",
        "prep_time": 20,
    },
    {
        "title": "Soy Glazed Salmon",
        "ingredients": ["salmon fillets", "soy sauce", "honey", "garlic", "lemon", "olive oil"],
        "instructions": "Whisk soy, honey, garlic. Brush over salmon. Bake at 400°F for 15 minutes, broil 2 minutes for glaze.",
        "cuisine": "Asian",
        "prep_time": 25,
    },
    {
        "title": "Classic Chicken Stir Fry",
        "ingredients": ["chicken breast", "broccoli", "soy sauce", "garlic", "ginger", "sesame oil", "cornstarch", "bell pepper"],
        "instructions": "Cut chicken into strips, coat in cornstarch. Stir fry on high heat with garlic and ginger. Add vegetables and soy sauce. Finish with sesame oil.",
        "cuisine": "Asian",
        "prep_time": 30,
    },
    {
        "title": "Lemon Herb Roasted Chicken",
        "ingredients": ["whole chicken", "lemon", "garlic", "rosemary", "thyme", "olive oil", "salt", "pepper"],
        "instructions": "Rub chicken with herb-garlic paste. Stuff with lemon halves. Roast at 425°F for 1 hour 20 minutes.",
        "cuisine": "French",
        "prep_time": 90,
    },
    {
        "title": "Teriyaki Chicken Bowl",
        "ingredients": ["chicken thighs", "soy sauce", "mirin", "sake", "sugar", "garlic", "rice", "broccoli"],
        "instructions": "Make teriyaki sauce from soy, mirin, sake, sugar. Pan-fry chicken, glaze with sauce. Serve over rice with broccoli.",
        "cuisine": "Japanese",
        "prep_time": 35,
    },
    {
        "title": "Honey Mustard Chicken",
        "ingredients": ["chicken breasts", "honey", "dijon mustard", "garlic", "olive oil", "rosemary"],
        "instructions": "Mix honey, mustard, garlic. Coat chicken. Bake at 375°F for 30 minutes. Rest before serving.",
        "cuisine": "American",
        "prep_time": 40,
    },
    {
        "title": "Spaghetti Aglio e Olio",
        "ingredients": ["spaghetti", "garlic", "olive oil", "red pepper flakes", "parsley", "parmesan"],
        "instructions": "Cook pasta. Sauté sliced garlic in olive oil with chili flakes until golden. Toss with pasta and pasta water. Top with parsley and parmesan.",
        "cuisine": "Italian",
        "prep_time": 20,
    },
    {
        "title": "Chicken Fried Rice",
        "ingredients": ["rice", "chicken", "eggs", "soy sauce", "garlic", "onion", "peas", "carrots", "sesame oil"],
        "instructions": "Use day-old rice. Stir fry garlic and onion. Add chicken, then rice. Push aside, scramble eggs. Mix everything with soy sauce and sesame oil.",
        "cuisine": "Asian",
        "prep_time": 25,
    },
    {
        "title": "Sweet and Sour Chicken",
        "ingredients": ["chicken breast", "pineapple", "bell pepper", "onion", "soy sauce", "vinegar", "sugar", "ketchup", "cornstarch"],
        "instructions": "Bread and fry chicken. Make sauce from vinegar, sugar, ketchup, pineapple juice. Toss with chicken and vegetables.",
        "cuisine": "Chinese",
        "prep_time": 50,
    },
    {
        "title": "Butter Chicken (Murgh Makhani)",
        "ingredients": ["chicken", "tomatoes", "butter", "cream", "garlic", "ginger", "garam masala", "cumin", "coriander", "turmeric"],
        "instructions": "Marinate chicken in yogurt and spices. Grill or pan fry. Simmer in tomato-butter sauce with cream until rich.",
        "cuisine": "Indian",
        "prep_time": 60,
    },
    {
        "title": "Pesto Pasta",
        "ingredients": ["pasta", "basil", "pine nuts", "parmesan", "garlic", "olive oil", "salt"],
        "instructions": "Blend basil, pine nuts, garlic, parmesan with olive oil. Toss with cooked pasta. Add pasta water to loosen.",
        "cuisine": "Italian",
        "prep_time": 20,
    },
    {
        "title": "Garlic Shrimp Scampi",
        "ingredients": ["shrimp", "garlic", "butter", "white wine", "lemon", "parsley", "pasta"],
        "instructions": "Sauté garlic in butter. Add shrimp, cook 2 min per side. Deglaze with wine and lemon. Toss with pasta and parsley.",
        "cuisine": "Italian",
        "prep_time": 25,
    },
    {
        "title": "Beef Tacos",
        "ingredients": ["ground beef", "taco seasoning", "tortillas", "lettuce", "tomato", "cheese", "sour cream", "salsa", "onion"],
        "instructions": "Brown beef with seasoning. Warm tortillas. Assemble with all toppings.",
        "cuisine": "Mexican",
        "prep_time": 20,
    },
    {
        "title": "Chicken Caesar Salad",
        "ingredients": ["chicken breast", "romaine lettuce", "parmesan", "croutons", "caesar dressing", "lemon", "garlic"],
        "instructions": "Grill or pan-fry seasoned chicken. Toss lettuce with dressing and parmesan. Top with chicken and croutons.",
        "cuisine": "American",
        "prep_time": 25,
    },
    {
        "title": "Mushroom Risotto",
        "ingredients": ["arborio rice", "mushrooms", "onion", "garlic", "white wine", "parmesan", "butter", "vegetable broth"],
        "instructions": "Sauté onion and garlic. Toast rice. Add wine. Ladle hot broth gradually, stirring constantly. Finish with parmesan and butter.",
        "cuisine": "Italian",
        "prep_time": 45,
    },
    {
        "title": "Korean Bibimbap",
        "ingredients": ["rice", "beef", "spinach", "carrots", "bean sprouts", "egg", "gochujang", "soy sauce", "sesame oil", "garlic"],
        "instructions": "Prepare each topping separately. Arrange over rice in bowl. Top with fried egg. Mix with gochujang sauce before eating.",
        "cuisine": "Korean",
        "prep_time": 40,
    },
    {
        "title": "Tom Yum Soup",
        "ingredients": ["shrimp", "lemongrass", "galangal", "kaffir lime leaves", "fish sauce", "lime juice", "chili", "mushrooms", "coconut milk"],
        "instructions": "Simmer lemongrass and galangal. Add mushrooms, shrimp. Season with fish sauce, lime. Stir in coconut milk. Add chilies to taste.",
        "cuisine": "Thai",
        "prep_time": 30,
    },
    {
        "title": "Greek Lemon Chicken",
        "ingredients": ["chicken", "lemon", "garlic", "olive oil", "oregano", "salt", "pepper", "potatoes"],
        "instructions": "Marinate chicken and potatoes in lemon, garlic, oregano, oil mixture. Roast at 400°F for 55 minutes.",
        "cuisine": "Greek",
        "prep_time": 70,
    },
    {
        "title": "Black Bean Tacos",
        "ingredients": ["black beans", "tortillas", "avocado", "salsa", "lime", "cumin", "garlic", "cheddar cheese"],
        "instructions": "Season and warm black beans with cumin and garlic. Mash slightly. Fill tortillas with beans, avocado, salsa. Squeeze lime.",
        "cuisine": "Mexican",
        "prep_time": 15,
    },
]


def generate_extended_dataset(base: list[dict], target: int = 500) -> list[dict]:
    """
    Expand the base dataset through realistic variation to reach target size.
    Used when the full RecipeBox dataset isn't available.
    """
    extended = list(base)
    variations = [
        ("Spicy", ["chili flakes", "jalapeño", "cayenne"]),
        ("Slow-Cooker", ["bay leaf", "worcestershire sauce"]),
        ("Air Fryer", ["cooking spray"]),
        ("One-Pan", ["olive oil", "salt", "pepper"]),
        ("5-Ingredient", []),
        ("Weeknight", []),
        ("Restaurant-Style", ["heavy cream", "butter"]),
        ("Healthy", ["olive oil", "lemon"]),
    ]

    cuisines = ["Italian", "Asian", "Mexican", "American", "Indian", "French", "Greek", "Thai", "Japanese", "Korean", "Chinese", "Mediterranean"]

    rng = random.Random(42)

    while len(extended) < target:
        base_recipe = rng.choice(base)
        prefix, extra_ings = rng.choice(variations)
        new_recipe = {
            "title": f"{prefix} {base_recipe['title']}",
            "ingredients": base_recipe["ingredients"] + [i for i in extra_ings if i not in base_recipe["ingredients"]],
            "instructions": base_recipe["instructions"],
            "cuisine": rng.choice(cuisines),
            "prep_time": max(5, base_recipe.get("prep_time", 30) + rng.randint(-10, 20)),
        }
        extended.append(new_recipe)

    return extended[:target]


def load_recipes_from_builtin(target: int = 500) -> list[Recipe]:
    """Load the built-in sample dataset, expanded to target size."""
    dataset = generate_extended_dataset(SAMPLE_RECIPES, target)
    recipes = []
    for i, r in enumerate(dataset):
        recipes.append(Recipe(
            id=i,
            title=r["title"],
            ingredients=r["ingredients"],
            instructions=r["instructions"],
            cuisine=r.get("cuisine", "Unknown"),
            prep_time=r.get("prep_time", 0),
        ))
    return recipes


def load_recipes_from_json(path: Path) -> list[Recipe]:
    """Load recipes from a JSON file (array of recipe objects)."""
    with open(path) as f:
        data = json.load(f)
    recipes = []
    for i, r in enumerate(data[:10000]):
        recipes.append(Recipe(
            id=i,
            title=r.get("title", "Untitled"),
            ingredients=r.get("ingredients", []),
            instructions=r.get("instructions", r.get("directions", "")),
            cuisine=r.get("cuisine", r.get("tags", ["Unknown"])[0] if r.get("tags") else "Unknown"),
            prep_time=_parse_time(r.get("prep_time", r.get("prepTime", 0))),
            source_url=r.get("url", r.get("source_url", "")),
        ))
    return recipes


def _parse_time(val) -> int:
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        match = re.search(r"(\d+)", val)
        return int(match.group(1)) if match else 0
    return 0
