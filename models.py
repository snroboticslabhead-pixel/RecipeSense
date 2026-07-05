import json
import os
from config import Config

class RecipeManager:
    """Loads and queries the recipe database."""

    def __init__(self):
        self.recipes = []
        self._ingredient_index = {}
        self._load()

    def _load(self):
        path = Config.RECIPES_FILE
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.recipes = json.load(f)
        else:
            self.recipes = []
        self._build_index()

    def _build_index(self):
        self._ingredient_index = {}
        for recipe in self.recipes:
            for ing in recipe.get("ingredients", []):
                name = ing["name"].lower().strip()
                self._ingredient_index.setdefault(name, []).append(recipe["id"])

    def get_all(self):
        return self.recipes

    def get_by_id(self, recipe_id):
        for r in self.recipes:
            if r["id"] == recipe_id:
                return r
        return None

    def get_by_cuisine(self, cuisine):
        return [r for r in self.recipes if r.get("cuisine", "").lower() == cuisine.lower()]

    def search(self, query=None, cuisine=None, difficulty=None, max_time=None, tags=None):
        results = self.recipes
        if query:
            q = query.lower()
            results = [r for r in results if
                       q in r["name"].lower() or
                       q in r.get("cuisine", "").lower() or
                       any(q in ing["name"].lower() for ing in r.get("ingredients", [])) or
                       any(q in t.lower() for t in r.get("tags", []))]
        if cuisine:
            results = [r for r in results if r.get("cuisine", "").lower() == cuisine.lower()]
        if difficulty:
            results = [r for r in results if r.get("difficulty", "").lower() == difficulty.lower()]
        if max_time:
            results = [r for r in results if (r.get("prep_time", 0) + r.get("cook_time", 0)) <= max_time]
        if tags:
            results = [r for r in results if any(t.lower() in [tg.lower() for tg in r.get("tags", [])] for t in tags)]
        return results

    def match_ingredients(self, user_ingredients, min_match=0.3):
        user_ings = set(i.lower().strip() for i in user_ingredients if i.strip())
        results = []

        for recipe in self.recipes:
            recipe_ings = set(ing["name"].lower().strip() for ing in recipe.get("ingredients", []))
            if not recipe_ings:
                continue

            matched = user_ings & recipe_ings
            missing = recipe_ings - user_ings
            match_pct = len(matched) / len(recipe_ings)

            if match_pct >= min_match:
                results.append({
                    "recipe": recipe,
                    "matched_ingredients": list(matched),
                    "missing_ingredients": list(missing),
                    "match_percent": round(match_pct * 100),
                    "total_ingredients": len(recipe_ings)
                })

        results.sort(key=lambda x: (-x["match_percent"], x["recipe"].get("cook_time", 999)))
        return results

    def get_all_ingredients(self):
        names = set()
        for r in self.recipes:
            for ing in r.get("ingredients", []):
                names.add(ing["name"].lower().strip())
        return sorted(names)

    def get_all_cuisines(self):
        cuisines = set(r.get("cuisine", "") for r in self.recipes if r.get("cuisine"))
        return sorted(cuisines)

    def get_all_tags(self):
        tags = set()
        for r in self.recipes:
            for t in r.get("tags", []):
                tags.add(t.lower())
        return sorted(tags)


class ScanResult:
    """Holds the result of an image scan for ingredients."""

    def __init__(self, ingredients=None, error=None, raw_text=None):
        self.ingredients = ingredients or []
        self.error = error
        self.raw_text = raw_text
