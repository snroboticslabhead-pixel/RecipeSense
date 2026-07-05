import io
import re
import time
import json
import base64
import zlib
import hashlib
import uuid
from urllib.parse import quote, unquote
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, stream_with_context
from werkzeug.security import check_password_hash
from google import genai
from PIL import Image
from openai import OpenAI
from config import Config
from database import (init_db, add_favorite, remove_favorite, get_favorites, is_favorited,
                      add_search_history, get_search_history, save_preferences, get_preferences,
                      create_user, get_user_by_email, get_user_by_id,
                      get_search_history_count, clear_search_history, clear_all_favorites, delete_user_account)
from models import RecipeManager, ScanResult

app = Flask(__name__)
app.config.from_object(Config)

# ── Image Maps ──
RECIPE_IMAGES = {
    1: "https://images.unsplash.com/photo-1612874742237-6526221588e3?w=800&q=80",
    2: "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=800&q=80",
    3: "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=800&q=80",
    4: "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=800&q=80",
    5: "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=800&q=80",
    6: "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=800&q=80",
    7: "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800&q=80",
    8: "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=800&q=80",
    9: "https://images.unsplash.com/photo-1600891964092-4316c288032e?w=800&q=80",
    10: "https://images.unsplash.com/photo-1590412200988-a436970781fa?w=800&q=80",
    11: "https://images.unsplash.com/photo-1559314809-0d155014e29e?w=800&q=80",
    12: "https://images.unsplash.com/photo-1528736235302-52922df5c122?w=800&q=80",
    13: "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=800&q=80",
    14: "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&q=80",
    15: "https://images.unsplash.com/photo-1562440499-64c9a111f713?w=800&q=80",
    16: "https://images.unsplash.com/photo-1577805947697-89e18249d767?w=800&q=80",
    17: "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=800&q=80",
    18: "https://images.unsplash.com/photo-1618040996337-56904b7850b9?w=800&q=80",
    19: "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=800&q=80",
    20: "https://images.unsplash.com/photo-1506084868230-bb9d95c24759?w=800&q=80",
    21: "https://images.unsplash.com/photo-1543339308-43e59d6b73a6?w=800&q=80",
    22: "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=800&q=80",
    23: "https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=800&q=80",
    24: "https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=800&q=80",
}

CUISINE_IMAGES = {
    "Indian": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=400&h=400&fit=crop&q=80",
    "Italian": "https://images.unsplash.com/photo-1498579150354-977475b7ea0b?w=400&h=400&fit=crop&q=80",
    "Asian": "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=400&h=400&fit=crop&q=80",
    "Mexican": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?w=400&h=400&fit=crop&q=80",
    "American": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400&h=400&fit=crop&q=80",
    "Mediterranean": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&h=400&fit=crop&q=80",
}

QUICK_PICK_IMAGES = {
    "Easy": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&h=400&fit=crop&q=80",
    "Under 30 Min": "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=600&h=400&fit=crop&q=80",
    "Healthy": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=600&h=400&fit=crop&q=80",
    "Comfort Food": "https://images.unsplash.com/photo-1504778703254-2cdc9a4b8a69?w=600&h=400&fit=crop&q=80",
}

INGREDIENT_EMOJIS = {
    "chicken breast": "🍗", "garlic": "🧄", "onion": "🧅", "tomato": "🍅",
    "rice": "🍚", "eggs": "🥚", "cheese": "🧀", "butter": "🧈",
    "olive oil": "🫒", "pasta": "🍝", "milk": "🥛", "salt": "🧂",
    "bell pepper": "🫑", "carrot": "🥕", "potato": "🥔", "broccoli": "🥦",
    "cilantro": "🌿", "parsley": "🌿", "basil": "🌿", "ginger": "🫚",
    "chili powder": "🌶️", "cumin": "🫙", "turmeric": "🟡", "soy sauce": "🥢",
    "lemon": "🍋", "lime": "🍋", "avocado": "🥑", "mushroom": "🍄",
    "shrimp": "🦐", "fish": "🐟", "beef": "🥩", "yogurt": "🥄",
    "cream": "🥛", "flour": "🌾", "sugar": "🍬", "bread": "🍞",
    "tortilla": "🌯", "lettuce": "🥬", "cucumber": "🥒", "corn": "🌽",
    "beans": "🫘", "lentils": "🫘", "coconut milk": "🥥", "sesame oil": "🫙",
    "green onion": "🧅", "mint": "🌿", "oregano": "🌿", "paprika": "🟠",
    "garam masala": "🫙", "black pepper": "🧂", "vanilla extract": "🍦",
    "baking powder": "🫙", "baking soda": "🫙", "cocoa powder": "🍫",
    "chickpeas": "🫘", "tahini": "🫙", "hummus": "🫙", "feta cheese": "🧀",
    "mozzarella cheese": "🧀", "parmesan cheese": "🧀", "cheddar cheese": "🧀",
    "naan": "🫓", "tortilla chips": "🌯", "salsa": "🫙", "sour cream": "🥄",
    "bean sprouts": "🌱", "rice noodles": "🍜", "rice vermicelli": "🍜",
    "rice paper wrappers": "📄", "peanuts": "🥜", "fish sauce": "🥢",
    "tamarind paste": "🫙", "jalapeño": "🌶️", "red pepper flakes": "🌶️",
    "white wine": "🍷", "vegetable broth": "🥣", "chicken broth": "🥣",
    "heavy cream": "🥛", "tomato puree": "🍅", "tomato sauce": "🍅",
    "all-purpose flour": "🌾", "arborio rice": "🍚", "saffron": "🟡",
    "ghee": "🧈", "banana": "🍌", "maple syrup": "🍁", "cornstarch": "🫙",
    "bread crumbs": "🍞", "balsamic vinegar": "🫗", "lemon juice": "🍋",
    "olives": "🫒", "red onion": "🧅", "sweet potato": "🍠",
    "ground beef": "🥩", "taco shells": "🌮", "vegetable oil": "🫒",
}

POPULAR_INGREDIENT_IMAGES = {
    "chicken breast": "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200&h=200&fit=crop&q=80",
    "garlic": "https://images.unsplash.com/photo-1540148426945-6cf22a6b2383?w=200&h=200&fit=crop&q=80",
    "onion": "https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?w=200&h=200&fit=crop&q=80",
    "tomato": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=200&h=200&fit=crop&q=80",
    "rice": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=200&h=200&fit=crop&q=80",
    "eggs": "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=200&h=200&fit=crop&q=80",
    "cheese": "https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=200&h=200&fit=crop&q=80",
    "butter": "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=200&h=200&fit=crop&q=80",
    "olive oil": "https://images.unsplash.com/photo-1474979266404-7caddbed77a3?w=200&h=200&fit=crop&q=80",
    "pasta": "https://images.unsplash.com/photo-1551462147-ff29053bfc14?w=200&h=200&fit=crop&q=80",
    "milk": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=200&h=200&fit=crop&q=80",
    "salt": "https://images.unsplash.com/photo-1518110925495-5fe2fda0442c?w=200&h=200&fit=crop&q=80",
}

# ── Template Filters ──
@app.template_filter('popular_ingredient_image')
def popular_ingredient_image_filter(value):
    return POPULAR_INGREDIENT_IMAGES.get(value.lower(), "")

@app.template_filter('from_json')
def from_json_filter(value):
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []

@app.template_filter('recipe_image')
def recipe_image_filter(recipe):
    rid = recipe.get("id")
    if rid and isinstance(rid, (int, float)):
        return RECIPE_IMAGES.get(int(rid), "")
    return ""

@app.template_filter('cuisine_image')
def cuisine_image_filter(cuisine):
    return CUISINE_IMAGES.get(cuisine, "")

@app.template_filter('quickpick_image')
def quickpick_image_filter(name):
    return QUICK_PICK_IMAGES.get(name, "")

@app.template_filter('ingredient_emoji')
def ingredient_emoji_filter(value):
    return INGREDIENT_EMOJIS.get(value.lower(), "🥘")

# ── Initialize Database ──
init_db()

# ── AI Client Initialization (Safe - no crash on missing keys) ──
gemini_client = None
groq_client = None

if Config.is_gemini_available():
    try:
        gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
        print("[INIT] Gemini client initialized successfully.")
    except Exception as e:
        print(f"[INIT] Gemini initialization failed: {e}")
        gemini_client = None
else:
    print("[INIT] WARNING: GEMINI_API_KEY not set. AI Scanner and Chat will be unavailable.")

if Config.is_groq_available():
    try:
        groq_client = OpenAI(
            api_key=Config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        print("[INIT] Groq client initialized successfully.")
    except Exception as e:
        print(f"[INIT] Groq initialization failed: {e}")
        groq_client = None
else:
    print("[INIT] WARNING: GROQ_API_KEY not set. AI Recipe Suggestions will be unavailable.")

recipe_manager = RecipeManager()

# ── Context Processor ──
@app.context_processor
def inject_user_state():
    user_id = session.get('user_id')
    if user_id:
        user = get_user_by_id(user_id)
        if user:
            return dict(is_logged_in=True, current_user=user)
        else:
            session.pop('user_id', None)
            session.pop('username', None)
    return dict(is_logged_in=False, current_user=None)

# ── Category Mapping ──
CATEGORY_MAP = {
    "Curries & Gravies": ["curry", "dal", "tadka", "gravy", "masala"],
    "Rice & Grains": ["rice", "biryani", "fried rice", "pilaf", "grain"],
    "Pasta & Noodles": ["pasta", "noodles", "spaghetti", "pad thai", "macaroni"],
    "Quick Meals": ["quick", "weeknight", "fast"],
    "Soups & Stews": ["soup", "stew", "broth"],
    "Appetizers & Snacks": ["appetizer", "snack", "no-cook", "dip", "hummus", "guacamole", "bruschetta"],
    "Breads & Baked": ["bread", "baking", "pizza", "mug cake", "banana bread", "pancake"],
    "Desserts & Sweets": ["dessert", "sweet", "cake", "chocolate"],
    "Healthy & Light": ["healthy", "low-calorie", "salad", "vegan", "light"],
    "Comfort Food": ["comfort", "cheesy", "creamy", "mac and cheese"],
    "One-Pot Wonders": ["one-pot", "one-pan"],
    "Breakfast": ["breakfast", "pancake", "shakshuka", "egg"],
}

def categorize_recipes(matched_results):
    categories = {}
    for item in matched_results:
        recipe = item["recipe"]
        tags = [t.lower() for t in recipe.get("tags", [])]
        name = recipe.get("name", "").lower()
        assigned = False
        for cat_name, cat_keywords in CATEGORY_MAP.items():
            for kw in cat_keywords:
                if kw in tags or kw in name:
                    categories.setdefault(cat_name, []).append(item)
                    assigned = True
                    break
            if assigned:
                break
        if not assigned:
            categories.setdefault("Other Dishes", []).append(item)
    return {k: v for k, v in sorted(categories.items(), key=lambda x: -len(x[1])) if v}

def get_device_id():
    if 'user_id' in session:
        return f"user_{session['user_id']}"
    if "device_id" not in session:
        session["device_id"] = request.headers.get("X-Device-ID", str(uuid.uuid4())[:12])
    return session["device_id"]

def extract_retry_seconds(error_message: str) -> int:
    match = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s", error_message)
    if match:
        return int(match.group(1))
    match2 = re.search(r"retry in ([\d.]+)s", error_message)
    if match2:
        return int(float(match2.group(1))) + 1
    return 60

def safe_json_parse(text):
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") or part.startswith("["):
                text = part
                break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for i, ch in enumerate(text):
        if ch in ('{', '['):
            try:
                return json.loads(text[i:])
            except json.JSONDecodeError:
                continue
    return None

def encode_ai_recipe(recipe_dict):
    raw = json.dumps(recipe_dict, ensure_ascii=False).encode("utf-8")
    compressed = zlib.compress(raw, 9)
    return quote(base64.urlsafe_b64encode(compressed).decode("ascii"))

def decode_ai_recipe(encoded):
    try:
        raw = base64.urlsafe_b64decode(unquote(encoded).encode("ascii"))
        decompressed = zlib.decompress(raw)
        return json.loads(decompressed.decode("utf-8"))
    except Exception as e:
        print(f"[decode_ai_recipe] error: {e}")
        return None

def normalize_recipe(recipe, source="database"):
    r = dict(recipe)
    r.setdefault("id", None)
    r.setdefault("source", source)
    r.setdefault("name", "Untitled Recipe")
    r.setdefault("emoji", "🍽️")
    r.setdefault("cuisine", "International")
    r.setdefault("category", "Main Course")
    r.setdefault("difficulty", "Medium")
    r.setdefault("prep_time", r.get("prep_time_minutes", 10))
    r.setdefault("cook_time", r.get("cook_time_minutes", 20))
    r.setdefault("servings", 2)
    r.setdefault("tags", [])
    r.setdefault("color_from", "#FFB75E")
    r.setdefault("color_to", "#ED8F47")
    r.setdefault("description", "")
    r.setdefault("summary", "")
    r.setdefault("tips", [])
    r.setdefault("rating", 4.5)
    r.setdefault("confidence", 0.92 if source == "ai" else 1.0)

    n = r.get("nutrition", {}) or {}
    r["nutrition"] = {
        "calories": n.get("calories", 0),
        "protein":  n.get("protein",  "0g"),
        "carbs":    n.get("carbs",    n.get("carbohydrates", "0g")),
        "fat":      n.get("fat",      "0g"),
        "fiber":    n.get("fiber",    "0g"),
        "sugar":    n.get("sugar",    "0g"),
        "sodium":   n.get("sodium",   "0mg"),
    }

    raw_ings = r.get("ingredients") or r.get("ingredients_list") or []
    ings = []
    for it in raw_ings:
        if isinstance(it, str):
            ings.append({"name": it, "amount": "", "available": True})
        elif isinstance(it, dict):
            ings.append({
                "name":      it.get("name", ""),
                "amount":    it.get("amount", it.get("quantity", "")),
                "available": bool(it.get("available", True)),
            })
    r["ingredients"] = ings

    raw_steps = r.get("steps", []) or []
    steps = []
    for i, s in enumerate(raw_steps):
        if isinstance(s, str):
            steps.append({"index": i + 1, "title": f"Step {i+1}", "instruction": s, "time_minutes": None, "difficulty": None})
        elif isinstance(s, dict):
            steps.append({
                "index": i + 1,
                "title": s.get("title", f"Step {i+1}"),
                "instruction": s.get("instruction", s.get("text", "")),
                "time_minutes": s.get("time_minutes"),
                "difficulty": s.get("difficulty"),
            })
    r["steps"] = steps

    r["timeline"] = {
        "prep":  r["prep_time"],
        "cook":  r["cook_time"],
        "rest":  r.get("rest_time", 0),
        "total": r["prep_time"] + r["cook_time"] + r.get("rest_time", 0),
    }
    return r

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PAGE ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/')
def index():
    device_id = get_device_id()
    fav_ids = get_favorites(device_id)
    history = get_search_history(device_id, limit=5)
    cuisines = recipe_manager.get_all_cuisines()
    featured = recipe_manager.search()[:6]
    recipes_count = len(recipe_manager.get_all())

    popular = ["chicken breast", "garlic", "onion", "tomato", "rice", "eggs", "cheese", "butter", "olive oil", "pasta", "milk", "salt"]
    all_recipes = recipe_manager.get_all()
    popular_ing_data = []
    for ing in popular:
        count = sum(1 for r in all_recipes if any(ing == i["name"].lower().strip() for i in r.get("ingredients", [])))
        popular_ing_data.append({"name": ing, "emoji": INGREDIENT_EMOJIS.get(ing, "🥘"), "image": POPULAR_INGREDIENT_IMAGES.get(ing, ""), "count": count})

    return render_template('index.html', featured=featured, cuisines=cuisines, fav_ids=fav_ids, history=history, recipes_count=recipes_count, popular_ingredients=popular_ing_data)

@app.route('/scanner')
def scanner():
    device_id = get_device_id()
    fav_ids = get_favorites(device_id)
    ai_status = {
        "scanner": bool(gemini_client),
        "suggest": bool(groq_client),
    }
    return render_template('scanner.html', fav_ids=fav_ids, ai_status=ai_status)

@app.route('/ingredients')
def ingredients():
    device_id = get_device_id()
    fav_ids = get_favorites(device_id)
    all_ingredients = recipe_manager.get_all_ingredients()
    popular = ["chicken breast", "garlic", "onion", "tomato", "rice", "eggs", "cheese", "butter", "olive oil", "pasta", "milk", "salt"]
    first_letters = sorted(set(ing[0].upper() for ing in all_ingredients if ing))
    return render_template('ingredients.html', all_ingredients=all_ingredients, popular=popular, fav_ids=fav_ids, first_letters=first_letters)

@app.route('/recipes')
def recipes():
    device_id = get_device_id()
    fav_ids = get_favorites(device_id)
    ingredients_param = request.args.get('ingredients', '')
    query = request.args.get('q', '')
    cuisine = request.args.get('cuisine', '')
    difficulty = request.args.get('difficulty', '')
    max_time = request.args.get('max_time', '')
    category_tag = request.args.get('tag', '')

    matched_results = None
    recipes_list = []
    search_ingredients = []

    if ingredients_param:
        search_ingredients = [i.strip() for i in ingredients_param.split(',') if i.strip()]
        add_search_history(device_id, ingredients_param)
        matched_results = recipe_manager.match_ingredients(search_ingredients, min_match=0.25)
        if category_tag:
            cat_keywords = CATEGORY_MAP.get(category_tag, [category_tag.lower()])
            filtered = []
            for item in matched_results:
                tags = [t.lower() for t in item["recipe"].get("tags", [])]
                name = item["recipe"].get("name", "").lower()
                for kw in cat_keywords:
                    if kw in tags or kw in name:
                        filtered.append(item)
                        break
            matched_results = filtered
    else:
        recipes_list = recipe_manager.search(query=query or None, cuisine=cuisine or None, difficulty=difficulty or None, max_time=int(max_time) if max_time else None)
        if query:
            add_search_history(device_id, query)

    cuisines = recipe_manager.get_all_cuisines()
    return render_template('recipes.html', recipes=recipes_list, matched=matched_results, search_ingredients=search_ingredients, query=query, cuisine=cuisine, difficulty=difficulty, max_time=max_time, cuisines=cuisines, fav_ids=fav_ids, category_tag=category_tag)

@app.route('/recipes/<int:recipe_id>')
def recipe_details(recipe_id):
    device_id = get_device_id()
    fav_ids = get_favorites(device_id)
    recipe = recipe_manager.get_by_id(recipe_id)
    if not recipe:
        return redirect(url_for('recipes'))
    recipe = normalize_recipe(recipe, source="database")
    related_raw = [r for r in recipe_manager.get_by_cuisine(recipe.get("cuisine", "")) if r["id"] != recipe_id][:3]
    related = [normalize_recipe(r, source="database") for r in related_raw]
    is_fav = recipe_id in fav_ids
    return render_template('recipe_details.html', recipe=recipe, related=related, is_fav=is_fav, fav_ids=fav_ids, search_ingredients=[])

@app.route('/recipes/ai')
def recipe_ai():
    encoded = request.args.get('recipe', '')
    device_id = get_device_id()
    fav_ids = get_favorites(device_id)

    recipe = None
    if encoded:
        recipe = decode_ai_recipe(encoded)
    if not recipe:
        cache_key = request.args.get('k', '')
        recipe = (session.get("ai_recipe_cache") or {}).get(cache_key)
    if not recipe:
        return redirect(url_for('scanner'))

    recipe = normalize_recipe(recipe, source="ai")
    h = hashlib.sha1(json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:10]
    cache = session.setdefault("ai_recipe_cache", {})
    cache[h] = recipe
    session.modified = True

    return render_template('recipe_details.html', recipe=recipe, related=[], is_fav=False, fav_ids=fav_ids, search_ingredients=[])

@app.route('/favorites')
def favorites():
    device_id = get_device_id()
    fav_ids = get_favorites(device_id)
    fav_recipes = [recipe_manager.get_by_id(rid) for rid in fav_ids]
    fav_recipes = [r for r in fav_recipes if r is not None]
    return render_template('favorites.html', recipes=fav_recipes, fav_ids=fav_ids)

@app.route('/chat')
def chat():
    device_id = get_device_id()
    fav_ids = get_favorites(device_id)
    ai_available = bool(gemini_client)
    return render_template('chat.html', fav_ids=fav_ids, recipe_images=RECIPE_IMAGES, ai_available=ai_available)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AUTH ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        return render_template('auth.html', mode='login', error="Invalid email or password.")
    return render_template('auth.html', mode='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not username or not email or not password:
            return render_template('auth.html', mode='register', error="All fields are required.")
        if len(password) < 6:
            return render_template('auth.html', mode='register', error="Password must be at least 6 characters.")
        user_id = create_user(username, email, password)
        if user_id:
            session['user_id'] = user_id
            session['username'] = username
            return redirect(url_for('index'))
        return render_template('auth.html', mode='register', error="Email already registered.")
    return render_template('auth.html', mode='register')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    device_id = get_device_id()
    fav_ids = get_favorites(device_id)
    prefs = get_preferences(device_id)
    cuisines = recipe_manager.get_all_cuisines()
    user = get_user_by_id(session['user_id'])
    history_count = get_search_history_count(device_id)
    created_at = user['created_at'] if user and user['created_at'] else None
    days_active = 1
    if created_at:
        try:
            from datetime import datetime
            created_date = datetime.strptime(str(created_at)[:10], '%Y-%m-%d')
            days_active = max(1, (datetime.now() - created_date).days)
        except:
            pass
    return render_template('profile.html', prefs=prefs, cuisines=cuisines, fav_ids=fav_ids, user=user, history_count=history_count, days_active=days_active)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if not gemini_client:
        return jsonify({'error': 'AI chat is unavailable. The GEMINI_API_KEY environment variable is not configured on the server.'}), 503

    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()
    history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    all_ingredients = recipe_manager.get_all_ingredients()
    all_cuisines = recipe_manager.get_all_cuisines()
    total_recipes = len(recipe_manager.get_all())

    recipe_index = []
    for r in recipe_manager.get_all():
        recipe_index.append({
            "id": r["id"], "name": r["name"], "cuisine": r.get("cuisine", ""),
            "difficulty": r.get("difficulty", ""),
            "time": r.get("prep_time", 0) + r.get("cook_time", 0),
            "ingredients": [ing["name"].lower() for ing in r.get("ingredients", [])]
        })

    system_instruction = (
        "You are ChefMate, a friendly and knowledgeable AI cooking assistant built into the RecipeSense app. "
        "Your personality is warm, encouraging, and practical — like a chef friend who loves helping people cook.\n\n"
        "RESPONSE FORMAT:\n"
        "- Use markdown: **bold** for emphasis, ## for section headers, - for bullet lists\n"
        "- Keep responses concise (3-5 paragraphs) unless the user asks for something detailed\n"
        "- Use ingredient emojis naturally: 🍅 tomato, 🧄 garlic, 🧅 onion, 🍗 chicken, 🥚 eggs, 🧀 cheese, 🧈 butter, 🫒 olive oil, 🥕 carrot, 🥔 potato, 🥦 broccoli, 🍚 rice, 🍝 pasta\n\n"
        "RECIPE REFERENCES:\n"
        "When you find a matching recipe from the database below, link it as [Recipe Name](/recipes/ID) — these become clickable in the app.\n"
        "Always prefer suggesting recipes from the database when they match the user's request.\n\n"
        "VIDEO LINKS & TUTORIAL LOOKUPS:\n"
        "Whenever a user asks for recipes, step-by-step cooking procedures, or specific kitchen methods, you MUST provide a distinct '📺 Video Tutorials & Guides' section.\n"
        "Generate helpful lookups using standard markdown hyperlinks with custom descriptive text. Format rules:\n"
        "1. Direct YouTube link lookup: [Watch video guide on YouTube](https://www.youtube.com/results?search_query=how+to+cook+[recipe_name_keywords])\n"
        "2. Google Video query lookup: [Search video tutorials on Google](https://www.google.com/search?q=[recipe_name_keywords]+recipe+video&tbm=vid)\n"
        "Be sure to clean and replace spaces inside '[recipe_name_keywords]' with plus symbols (+).\n\n"
        f"APP DATABASE ({total_recipes} recipes):\n"
        f"Cuisines: {', '.join(all_cuisines)}\n"
        f"Ingredients available: {', '.join(all_ingredients[:100])}\n\n"
        f"RECIPE INDEX:\n{json.dumps(recipe_index, ensure_ascii=False)}\n\n"
        "BEHAVIOR:\n"
        "- For ingredient-based queries, search the recipe index and suggest the best matches\n"
        "- For technique questions, give clear step-by-step instructions accompanied by explicit video guides lookups\n"
        "- For substitutions, explain WHY it works and what differences to expect\n"
        "- For meal planning, be practical and consider variety\n"
        "- For nutrition questions, give reasonable estimates but note they're approximate\n"
        "- For food safety, reference USDA/FDA guidelines cautiously\n"
        "- Never give medical nutrition advice for specific health conditions\n"
        "- Be enthusiastic about food!\n\n"
        "FOLLOW-UP SUGGESTIONS:\n"
        "At the end of your response, if appropriate, suggest 2-3 follow-up questions the user might ask. "
        "Put them on their own line formatted EXACTLY as: [SUGGESTIONS: question one | question two | question three]\n"
        "Only include suggestions when they feel natural, not on every single response."
    )

    gemini_contents = []
    for msg in history[-16:]:
        role = "user" if msg.get("role") == "user" else "model"
        gemini_contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
    gemini_contents.append({"role": "user", "parts": [{"text": user_message}]})

    def generate_stream():
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = gemini_client.models.generate_content(
                    model=Config.GEMINI_MODEL,
                    contents=gemini_contents,
                    config={
                        "system_instruction": system_instruction,
                        "temperature": 0.8,
                        "top_p": 0.95,
                        "max_output_tokens": 2048,
                    }
                )
                full_text = response.text
                chunk_size = 3
                for i in range(0, len(full_text), chunk_size):
                    yield full_text[i:i + chunk_size]
                    time.sleep(0.015)
                return
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    wait = extract_retry_seconds(error_msg)
                    if attempt < max_retries - 1:
                        time.sleep(wait)
                        continue
                    yield f"**API quota exhausted.** Please wait about {wait} seconds and try again."
                    return
                if "503" in error_msg or "high demand" in error_msg.lower():
                    wait = extract_retry_seconds(error_msg)
                    if attempt < max_retries - 1:
                        time.sleep(wait)
                        continue
                    yield "**AI engine is currently busy.** Please try again in a moment."
                    return
                # Handle 403 specifically
                if "403" in error_msg or "PERMISSION_DENIED" in error_msg:
                    yield "**Error:** API key permission denied. The Gemini API key may be invalid, leaked, or revoked. Please contact the admin to set a new API key in the server environment variables."
                    return
                yield f"**Error:** {error_msg}"
                return

    return Response(
        stream_with_context(generate_stream()),
        mimetype='text/plain',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )

@app.route('/api/scan', methods=['POST'])
def api_scan():
    if not gemini_client:
        return jsonify({'error': 'AI scanner is unavailable. GEMINI_API_KEY is not configured on the server.'}), 503
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided.'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400
    try:
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))
        prompt = (
            "You are a food ingredient identification system. Analyze this image and identify "
            "ALL food items, ingredients, and cooking materials visible. Return ONLY a valid JSON "
            "array of lowercase ingredient names as strings. Include only items that are actual "
            "food ingredients usable in cooking. Do not include utensils, plates, or non-food items. "
            "Example: [\"tomato\", \"onion\", \"chicken breast\", \"garlic\", \"olive oil\"]\n"
            "Return ONLY the JSON array, nothing else."
        )
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = gemini_client.models.generate_content(model=Config.GEMINI_MODEL, contents=[image, prompt])
                raw_text = response.text.strip()
                ingredients = safe_json_parse(raw_text)
                if isinstance(ingredients, list):
                    cleaned = []
                    for ing in ingredients:
                        if isinstance(ing, str):
                            cleaned.append(ing.lower().strip())
                        elif isinstance(ing, dict) and "name" in ing:
                            cleaned.append(ing["name"].lower().strip())
                    return jsonify({'ingredients': cleaned, 'raw': raw_text})
                return jsonify({'ingredients': [], 'raw': raw_text, 'error': 'Unexpected format'})
            except json.JSONDecodeError:
                raw_text = response.text.strip()
                items = re.findall(r'["\']?([a-z][a-z\s]+?)["\']?(?:\s*[,;\n]|\s*$)', raw_text, re.I)
                if items:
                    return jsonify({'ingredients': [i.lower().strip() for i in items if len(i.strip()) > 2], 'raw': raw_text})
                return jsonify({'ingredients': [], 'raw': raw_text, 'error': 'Could not parse'})
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "PERMISSION_DENIED" in error_msg:
                    return jsonify({'error': 'API key permission denied. The Gemini API key is invalid or revoked. Contact admin to set a new key.'}), 403
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    wait = extract_retry_seconds(error_msg)
                    if attempt < max_retries - 1:
                        time.sleep(wait)
                        continue
                    return jsonify({'error': f'Quota exhausted. Wait {wait}s.', 'retry_after': wait}), 429
                if "503" in error_msg or "high demand" in error_msg.lower():
                    wait = extract_retry_seconds(error_msg)
                    if attempt < max_retries - 1:
                        time.sleep(wait)
                        continue
                    return jsonify({'error': 'AI busy. Retry.', 'retry_after': wait}), 503
                raise e
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan/ai-suggest', methods=['POST'])
def api_ai_suggest():
    if not groq_client:
        return jsonify({'error': 'AI recipe engine (Groq) is unavailable. GROQ_API_KEY is not configured on the server.'}), 503

    data = request.get_json(silent=True) or {}
    ingredients = data.get("ingredients", [])
    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400

    ingredients_lower = [i.lower().strip() for i in ingredients if i.strip()]
    ingredients_str = ", ".join(ingredients_lower)

    system_prompt = """You are a world-class professional chef. Your task is to generate diverse recipe suggestions based on the provided ingredients. 
You must return ONLY a valid JSON object with the exact structure requested, no markdown, no explanation, no conversational text."""

    user_prompt = f"""A user has these ingredients in their kitchen:
{ingredients_str}

Generate 8 to 12 diverse recipe suggestions they can make. Group them into meaningful categories like:
- Curries & Gravies
- Rice & Grains
- Quick Meals (under 20 min)
- Soups
- Appetizers & Snacks
- Breakfast
- Desserts & Sweets
- Healthy & Light
- Comfort Food

For EACH recipe provide:
1. name - creative but clear recipe name
2. emoji - a single relevant food emoji
3. difficulty - Easy, Medium, or Hard
4. prep_time_minutes - integer
5. cook_time_minutes - integer
6. servings - integer
7. have_all_ingredients - boolean (true if ALL needed ingredients are in the user's list)
8. matched_ingredients - array of ingredient names from user's list that this recipe uses
9. missing_ingredients - array of ingredient names NOT in user's list that this recipe needs (empty array if have_all is true)
10. description - one compelling sentence describing the dish
11. ingredients_list - array of objects with "name" (string), "amount" (string like "2 cups"), "available" (boolean - true if in user's list)
12. steps - array of 4-8 clear step-by-step cooking instructions as strings
13. nutrition - object with calories (int), protein (string like "28g"), carbs (string), fat (string), fiber (string)
14. tags - array of 3-5 relevant tags as lowercase strings

IMPORTANT RULES:
- Be realistic about what can actually be made with these ingredients
- Assume the user has basic pantry staples: salt, pepper, water, cooking oil
- If a recipe needs 1-2 extra items, still include it but mark missing_ingredients
- Include recipes where the user has ALL ingredients AND recipes where they're missing just 1-2 things
- Make steps detailed and actionable
- Nutritional values should be realistic estimates per serving

Return ONLY a valid JSON object with this EXACT structure, no markdown, no explanation:
{{
"categories": [
{{
"name": "Category Name",
"recipes": [
{{
"name": "Recipe Name",
"emoji": "🍛",
"difficulty": "Easy",
"prep_time_minutes": 10,
"cook_time_minutes": 25,
"servings": 4,
"have_all_ingredients": true,
"matched_ingredients": ["onion", "tomato"],
"missing_ingredients": [],
"description": "A delicious...",
"ingredients_list": [
{{"name": "onion", "amount": "1 large", "available": true}},
{{"name": "cumin", "amount": "1 tsp", "available": false}}
],
"steps": ["Step one...", "Step two..."],
"nutrition": {{"calories": 350, "protein": "28g", "carbs": "12g", "fat": "20g", "fiber": "3g"}},
"tags": ["spicy", "comfort"]
}}
]
}}
]
}}"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = groq_client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=8000,
                response_format={"type": "json_object"}
            )

            raw_text = response.choices[0].message.content
            if not raw_text:
                return jsonify({"total_matches": 0, "ingredients": ingredients_lower, "categories": [], "source": "ai", "error": "AI returned empty response."})

            raw_text = raw_text.strip()
            parsed = safe_json_parse(raw_text)

            if parsed and "categories" in parsed and isinstance(parsed["categories"], list):
                valid_categories = []
                total_recipes = 0
                for cat in parsed["categories"]:
                    if not cat.get("name") or not isinstance(cat.get("recipes"), list):
                        continue
                    valid_recipes = []
                    for r in cat["recipes"]:
                        if not r.get("name"):
                            continue
                        r.setdefault("emoji", "🍽️")
                        r.setdefault("difficulty", "Medium")
                        r.setdefault("prep_time_minutes", 10)
                        r.setdefault("cook_time_minutes", 20)
                        r.setdefault("servings", 2)
                        r.setdefault("have_all_ingredients", False)
                        r.setdefault("matched_ingredients", [])
                        r.setdefault("missing_ingredients", [])
                        r.setdefault("description", "")
                        r.setdefault("ingredients_list", [])
                        r.setdefault("steps", [])
                        r.setdefault("nutrition", {"calories": 0, "protein": "0g", "carbs": "0g", "fat": "0g", "fiber": "0g"})
                        r.setdefault("tags", [])
                        r["view_url"] = "/recipes/ai?recipe=" + encode_ai_recipe(r)
                        valid_recipes.append(r)
                    if valid_recipes:
                        valid_categories.append({"name": cat["name"], "recipes": valid_recipes})
                        total_recipes += len(valid_recipes)

                return jsonify({"total_matches": total_recipes, "ingredients": ingredients_lower, "categories": valid_categories, "source": "ai"})

            return jsonify({"total_matches": 0, "ingredients": ingredients_lower, "categories": [], "source": "ai", "raw": raw_text, "error": "AI returned unexpected format. Try again."})

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "rate_limit" in error_msg.lower():
                wait = extract_retry_seconds(error_msg)
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    continue
                return jsonify({'error': f'API quota exhausted. Wait {wait}s.', 'retry_after': wait}), 429
            if "503" in error_msg or "high demand" in error_msg.lower():
                wait = extract_retry_seconds(error_msg)
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    continue
                return jsonify({'error': 'AI engine busy. Retry.', 'retry_after': wait}), 503
            if "403" in error_msg or "PERMISSION_DENIED" in error_msg or "authentication" in error_msg.lower():
                return jsonify({'error': 'Groq API key is invalid or revoked. Contact admin to set a new key.'}), 403
            return jsonify({'error': str(e), 'raw': error_msg}), 500

@app.route('/api/scan/categories', methods=['POST'])
def api_scan_categories():
    data = request.get_json(silent=True) or {}
    ingredients = data.get("ingredients", [])
    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400

    matched = recipe_manager.match_ingredients(ingredients, min_match=0.25)
    categories = categorize_recipes(matched)

    result = {"total_matches": len(matched), "ingredients": ingredients, "categories": {}, "source": "local"}
    for cat_name, items in categories.items():
        result["categories"][cat_name] = {
            "count": len(items),
            "top_match": items[0]["match_percent"] if items else 0,
            "recipes": [{
                "id": item["recipe"]["id"], "name": item["recipe"]["name"],
                "emoji": item["recipe"]["emoji"], "color_from": item["recipe"]["color_from"],
                "color_to": item["recipe"]["color_to"], "cuisine": item["recipe"]["cuisine"],
                "prep_time": item["recipe"]["prep_time"], "cook_time": item["recipe"]["cook_time"],
                "difficulty": item["recipe"]["difficulty"], "match_percent": item["match_percent"],
                "missing_count": len(item["missing_ingredients"]),
                "have_all": len(item["missing_ingredients"]) == 0
            } for item in items]
        }
    return jsonify(result)

@app.route('/api/recipes')
def api_recipes():
    query = request.args.get('q', '')
    cuisine = request.args.get('cuisine', '')
    difficulty = request.args.get('difficulty', '')
    max_time = request.args.get('max_time', '')
    ingredients = request.args.get('ingredients', '')

    if ingredients:
        ings = [i.strip() for i in ingredients.split(',') if i.strip()]
        results = recipe_manager.match_ingredients(ings, min_match=0.25)
        return jsonify([{'recipe': r['recipe'], 'match_percent': r['match_percent'], 'matched_ingredients': r['matched_ingredients'], 'missing_ingredients': r['missing_ingredients']} for r in results])

    recipes = recipe_manager.search(query=query or None, cuisine=cuisine or None, difficulty=difficulty or None, max_time=int(max_time) if max_time else None)
    return jsonify(recipes)

@app.route('/api/recipes/<int:recipe_id>')
def api_recipe_detail(recipe_id):
    recipe = recipe_manager.get_by_id(recipe_id)
    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    return jsonify(recipe)

@app.route('/api/ingredients/suggest')
def api_ingredient_suggest():
    q = request.args.get('q', '').lower().strip()
    if not q or len(q) < 2:
        return jsonify([])
    all_ings = recipe_manager.get_all_ingredients()
    matches = [ing for ing in all_ings if q in ing][:10]
    return jsonify(matches)

@app.route('/api/favorites', methods=['GET'])
def api_get_favorites():
    device_id = get_device_id()
    return jsonify(get_favorites(device_id))

@app.route('/api/favorites/<int:recipe_id>', methods=['POST', 'DELETE'])
def api_toggle_favorite(recipe_id):
    device_id = get_device_id()
    recipe = recipe_manager.get_by_id(recipe_id)
    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    if request.method == 'POST':
        add_favorite(device_id, recipe_id)
        return jsonify({'status': 'added', 'recipe_id': recipe_id})
    else:
        remove_favorite(device_id, recipe_id)
        return jsonify({'status': 'removed', 'recipe_id': recipe_id})

@app.route('/api/preferences', methods=['GET', 'POST'])
def api_preferences():
    device_id = get_device_id()
    if request.method == 'GET':
        return jsonify(get_preferences(device_id))
    data = request.get_json()
    save_preferences(device_id, data)
    return jsonify({'status': 'saved'})

@app.route('/api/history', methods=['DELETE'])
def api_clear_history():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    clear_search_history(get_device_id())
    return jsonify({'status': 'cleared'})

@app.route('/api/favorites/all', methods=['DELETE'])
def api_clear_all_favorites():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    clear_all_favorites(get_device_id())
    return jsonify({'status': 'cleared'})

@app.route('/api/account/delete', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    user_id = session['user_id']
    success = delete_user_account(user_id)
    if success:
        session.clear()
        return jsonify({'status': 'deleted'})
    return jsonify({'error': 'Failed to delete account'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
