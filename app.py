import streamlit as st
import json
import re
from typing import List, Dict
from pydantic import BaseModel
from google import genai
from google.genai import types

# 1. Page Configuration
st.set_page_config(page_title="herbie | Your Kitchen Sidekick", page_icon="🌿", layout="wide")

# --- NATIVE STABLE APP THEMING ---
st.markdown("""
 <style>
 @import url('https://fonts.googleapis.com/css2?family=League+Spartan:wght@700;800;900&family=Montserrat:wght@300;400;500&display=swap');
 
 .stApp, p, li, label, span {
     font-family: 'Montserrat', sans-serif !important;
     font-weight: 400;
     color: #24140B !important; 
 }

 h1, h2, h3, h4, h5, h6, [data-baseweb="tab"] p {
     font-family: 'League Spartan', 'Arial Black', sans-serif !important;
     text-transform: uppercase !important;
     letter-spacing: 0.5px !important;
     color: #24140B !important;
 }
    
 button[data-baseweb="tab"] p {
     color: #FF5A00 !important;
     font-size: 1.1rem !important;
 }
    
 .stApp {
     background-color: #FFF5EE !important; 
 }

 .block-container {
     max-width: 900px !important;
     padding-top: 2rem !important;
     padding-bottom: 2rem !important;
     margin: 0 auto !important;
 }

 [data-testid="stHeader"] {
     background-color: transparent !important;
 }
    
 .stSelectbox div, .stTextInput div, .stNumberInput div {
     background-color: #FFFFFF !important;
     border-radius: 8px !important;
 }

 div[data-testid="stCheckbox"] label span div {
     background-color: #FFFFFF !important;
     border: 1px solid #FFE4D3 !important;
     color: #24140B !important;
 }
 div[data-testid="stCheckbox"] p {
     color: #24140B !important;
 }
    
 textarea {
     background-color: #FFFFFF !important;
     border: 2px solid #00A8FF !important; 
     border-radius: 12px !important;
     color: #24140B !important;
     font-family: monospace !important;
     font-size: 1.1rem !important;
 }
 
 .macro-badge {
     background-color: #FFFFFF !important;
     border: 1px solid #FFE4D3 !important;
     padding: 4px 12px;
     border-radius: 20px;
     font-size: 0.85rem;
     display: inline-block;
     margin: 4px 6px 4px 0px;
     color: #FF5A00 !important;
     font-weight: bold;
     font-family: 'League Spartan', sans-serif !important;
     box-shadow: 0px 1px 3px rgba(0,0,0,0.05);
 }
 
 .cooking-box {
     background-color: #FFFFFF !important;
     border-left: 4px solid #00A8FF !important;
     padding: 14px 18px;
     border-radius: 4px 12px 12px 4px;
     margin-top: 6px;
     margin-bottom: 10px;
     box-shadow: 0px 2px 4px rgba(0,0,0,0.02);
 }

 div.stButton > button {
     background-color: #FFFFFF !important;
     color: #FF5A00 !important;
     border: 2px solid #FFE4D3 !important;
     border-radius: 8px !important;
     font-family: 'League Spartan', sans-serif !important;
     text-transform: uppercase !important;
     font-weight: 700 !important;
     transition: all 0.3s ease;
 }

 div.stButton > button:hover {
     border-color: #FF5A00 !important;
     background-color: #FFF5EE !important;
     color: #FF5A00 !important;
 }
 </style>
""", unsafe_allow_html=True)

# --- APP HEADER ---
st.write("<h1 style='color: #FF5A00; font-weight: 900; font-size: 3.5rem; margin-bottom: 0; letter-spacing: -1px;'>🌿 HERBIE</h1>", unsafe_allow_html=True)

# --- INITIALIZE STORAGE CATCHES ---
if "saved_links" not in st.session_state:
    st.session_state.saved_links = []
if "past_recipes" not in st.session_state:
    st.session_state.past_recipes = []

tab1, tab2, tab3 = st.tabs(["✨ Meal Planner", "📖 My Recipe Book", "⏳ Past Recipes"])

# ==========================================
# STRUCTURED PYDANTIC SCHEMAS FOR LLM ENGINE
# ==========================================
class IngredientItem(BaseModel):
    name: str
    amount: float
    unit: str

class RecipeItem(BaseModel):
    title: str
    image_emoji: str
    calories: str
    protein: str
    carbs: str
    fat: str
    instructions: str
    ingredients: List[IngredientItem]

class DayMenu(BaseModel):
    day_number: int
    breakfast: RecipeItem
    lunch: RecipeItem
    dinner: RecipeItem

class WeeklyPlan(BaseModel):
    days: List[DayMenu]

# ==========================================
# TAB 1: THE MEAL PLANNER (LLM ENGINE)
# ==========================================
with tab1:
    st.markdown("<p style='font-size: 1.1rem; font-weight: 400; color: #00A8FF !important; margin-top:5px;'>Your AI-powered weekly meal planner & grocery generator.</p>", unsafe_allow_html=True)
    st.markdown("<hr style='border-top: 2px solid #FFE4D3; margin-top: 10px; margin-bottom: 15px;'>", unsafe_allow_html=True)

    # API Key retrieval from Streamlit secrets or sidebar input
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        with st.sidebar:
            st.markdown("### 🔑 API Key Configuration")
            api_key = st.text_input("Gemini API Key", type="password", help="Enter your Gemini API key from Google AI Studio.")
            st.caption("Tip: Add GEMINI_API_KEY to your Streamlit secrets to hide this.")

    st.write("<h3 style='color: #FF5A00; font-weight: 800;'>📋 Step 1: Your Preferences</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        diet = st.selectbox("Do you follow a specific diet?", ["No Preference", "Vegetarian", "Vegan", "Gluten Free", "Ketogenic", "Mediterranean"])
        days = st.slider("How many days are you cooking for?", min_value=1, max_value=7, value=5)
    with col2:
        dislikes = st.text_input("Any ingredients to exclude?", placeholder="e.g., mushrooms, cilantro")
        servings = st.number_input("How many servings per meal?", min_value=1, max_value=10, value=2)

    st.markdown("<br><p style='font-size: 1.1rem; margin-bottom: 5px; font-weight: 700; color: #24140B;'>⚡ What appliances do you want to use?</p>", unsafe_allow_html=True)
    
    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
    with row1_col1: has_stove = st.checkbox("Stove", value=True)
    with row1_col2: has_oven = st.checkbox("Oven", value=True)
    with row1_col3: has_airfryer = st.checkbox("Air Fryer", value=True)
    with row1_col4: has_slowcooker = st.checkbox("Slow Cooker", value=False)
        
    row2_col1, row2_col2, row2_col3, _ = st.columns(4)
    with row2_col1: has_instantpot = st.checkbox("Instant Pot", value=False)
    with row2_col2: has_microwave = st.checkbox("Microwave", value=False)
    with row2_col3: has_blender = st.checkbox("Blender", value=False)

    allowed_appliances = []
    if has_stove: allowed_appliances.append("stove")
    if has_oven: allowed_appliances.append("oven")
    if has_airfryer: allowed_appliances.append("air fryer")
    if has_slowcooker: allowed_appliances.append("slow cooker")
    if has_instantpot: allowed_appliances.append("instant pot")
    if has_microwave: allowed_appliances.append("microwave")
    if has_blender: allowed_appliances.append("blender")

    # Offline backup catalogue in case the API is offline
    backup_db = {
        "Breakfast": [
            {"title": "Cinnamon Berry Protein Oats", "image": "🥣", "diets": ["No Preference", "Vegetarian", "Gluten Free", "Mediterranean"], "appliances": ["stove", "microwave"], "macros": {"Calories": "360 kcal", "Protein": "30g", "Carbs": "42g", "Fat": "6g"}, "instructions": "1. Simmer rolled oats in almond milk. 2. Stir in vanilla protein powder and cinnamon. 3. Top with fresh blueberries.", "ingredients": {"rolled oats": {"amount": 0.5, "unit": "cup"}, "protein powder": {"amount": 1.0, "unit": "scoop"}, "blueberries": {"amount": 0.5, "unit": "cup"}, "cinnamon": {"amount": 0.5, "unit": "teaspoon"}}},
            {"title": "Vanilla Almond Chia Seed Pudding", "image": "🍧", "diets": ["No Preference", "Vegetarian", "Vegan", "Gluten Free", "Mediterranean"], "appliances": ["stove", "oven", "air fryer", "slow cooker", "instant pot", "microwave", "blender"], "macros": {"Calories": "290 kcal", "Protein": "12g", "Carbs": "26g", "Fat": "16g"}, "instructions": "1. Whisk chia seeds, almond milk, and vanilla extract. 2. Chill overnight. 3. Top with sliced almonds.", "ingredients": {"chia seeds": {"amount": 3.0, "unit": "tablespoons"}, "almond milk": {"amount": 1.0, "unit": "cup"}, "sliced almonds": {"amount": 2.0, "unit": "tablespoons"}}}
        ],
        "Lunch": [
            {"title": "Mediterranean Quinoa Salad Bowls", "image": "🥗", "diets": ["No Preference", "Vegetarian", "Vegan", "Gluten Free", "Mediterranean"], "appliances": ["stove"], "macros": {"Calories": "460 kcal", "Protein": "16g", "Carbs": "64g", "Fat": "14g"}, "instructions": "1. Cook quinoa and cool. 2. Toss with chickpeas, diced cucumber, and tomatoes. 3. Dress with olive oil and lemon.", "ingredients": {"quinoa": {"amount": 0.75, "unit": "cup"}, "chickpeas": {"amount": 1.0, "unit": "can"}, "cucumber": {"amount": 1.0, "unit": "large"}, "cherry tomatoes": {"amount": 0.5, "unit": "pint"}, "olive oil": {"amount": 1.0, "unit": "tablespoon"}}},
            {"title": "Crispy Air Fryer Tofu Bowls with Rice", "image": "🧆", "diets": ["No Preference", "Vegetarian", "Vegan", "Gluten Free"], "appliances": ["stove", "oven", "air fryer"], "macros": {"Calories": "510 kcal", "Protein": "28g", "Carbs": "62g", "Fat": "15g"}, "instructions": "1. Cube pressed tofu, toss with oil, salt, and cornstarch. 2. Air fry at 400°F for 18 mins. 3. Serve over jasmine rice with peppers.", "ingredients": {"extra firm tofu": {"amount": 1.0, "unit": "block"}, "jasmine rice": {"amount": 0.75, "unit": "cup"}, "bell peppers": {"amount": 2.0, "unit": "medium"}}}
        ],
        "Dinner": [
            {"title": "Sheet Pan Chicken Sausage & Sweet Potato Bake", "image": "🍗", "diets": ["No Preference", "Gluten Free"], "appliances": ["oven"], "macros": {"Calories": "590 kcal", "Protein": "39g", "Carbs": "56g", "Fat": "23g"}, "instructions": "1. Slice chicken sausage, sweet potatoes, and zucchini. 2. Toss on sheet pan with olive oil and garlic. 3. Roast at 400°F for 28 mins.", "ingredients": {"chicken sausage": {"amount": 4.0, "unit": "links"}, "sweet potatoes": {"amount": 2.0, "unit": "medium"}, "zucchini": {"amount": 2.0, "unit": "medium"}, "olive oil": {"amount": 1.5, "unit": "tablespoons"}}},
            {"title": "Turkey & Black Bean Chili over Quinoa", "image": "🍲", "diets": ["No Preference", "Gluten Free", "Mediterranean"], "appliances": ["stove", "slow cooker", "instant pot"], "macros": {"Calories": "580 kcal", "Protein": "46g", "Carbs": "68g", "Fat": "10g"}, "instructions": "1. Brown turkey with onions. 2. Add black beans, tomato sauce, and chili spices. 3. Simmer 20 mins and ladle over warm quinoa.", "ingredients": {"ground turkey": {"amount": 1.25, "unit": "lbs"}, "black beans": {"amount": 1.0, "unit": "can"}, "quinoa": {"amount": 1.0, "unit": "cup"}, "tomato sauce": {"amount": 15.0, "unit": "oz"}}}
        ]
    }

    generate_clicked = st.button("✨ Generate AI Meal Plan", type="primary")

    selected_menu = []

    if generate_clicked:
        with st.spinner("Herbie is curating your personalized meal plan..."):
            if api_key:
                try:
                    client = genai.Client(api_key=api_key)
                    
                    prompt = f"""
                    You are Herbie, an expert chef and meal planner.
                    Create a {days}-day meal plan (Breakfast, Lunch, Dinner for each day).
                    Dietary Restriction: {diet}.
                    Strict Exclusions: {dislikes if dislikes else "None"}.
                    Only use recipes cookable with these available appliances: {', '.join(allowed_appliances) if allowed_appliances else "stove, oven"}.
                    Base single-batch ingredient measurements for 2 servings.
                    Keep instructions clear, step-by-step, and concise.
                    """

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=WeeklyPlan,
                            temperature=0.4
                        ),
                    )

                    parsed_plan = WeeklyPlan.model_validate_json(response.text)

                    for day in parsed_plan.days:
                        day_dict = {}
                        for slot_name, meal in [("Breakfast", day.breakfast), ("Lunch", day.lunch), ("Dinner", day.dinner)]:
                            ingredients_dict = {
                                item.name.lower(): {"amount": item.amount, "unit": item.unit}
                                for item in meal.ingredients
                            }
                            day_dict[slot_name] = {
                                "title": meal.title,
                                "image": meal.image_emoji if meal.image_emoji else "🥘",
                                "macros": {
                                    "Calories": meal.calories,
                                    "Protein": meal.protein,
                                    "Carbs": meal.carbs,
                                    "Fat": meal.fat
                                },
                                "instructions": meal.instructions,
                                "ingredients": ingredients_dict
                            }
                        selected_menu.append(day_dict)
                    st.session_state.active_menu = selected_menu
                except Exception as e:
                    st.error(f"AI Generation error: {e}. Falling back to internal recipe catalogue.")
            else:
                st.info("No Gemini API Key provided. Using Herbie's offline fallback recipes.")

    # Check session state for existing menu
    if "active_menu" in st.session_state and not selected_menu:
        selected_menu = st.session_state.active_menu

    # Fallback if no LLM menu was produced
    if not selected_menu and generate_clicked:
        import copy
        for i in range(days):
            day_dict = {}
            for slot in ["Breakfast", "Lunch", "Dinner"]:
                choices = backup_db.get(slot, [])
                chosen = copy.deepcopy(choices[i % len(choices)])
                day_dict[slot] = chosen
            selected_menu.append(day_dict)
        st.session_state.active_menu = selected_menu

    st.markdown("<hr style='border-top: 2px solid #FFE4D3; margin-top: 20px; margin-bottom: 20px;'>", unsafe_allow_html=True)
    st.write("<h3 style='color: #FF5A00; font-weight: 800;'>🍽️ Step 2: Your Weekly Menu</h3>", unsafe_allow_html=True)

    if not selected_menu:
        st.write("Click **✨ Generate AI Meal Plan** above to build your menu.")
    else:
        for day_set in selected_menu:
            for slot, recipe in day_set.items():
                if not any(past.get('title') == recipe['title'] for past in st.session_state.past_recipes):
                    st.session_state.past_recipes.append(recipe)

        for idx, day_set in enumerate(selected_menu):
            st.write(f"<h3 style='color: #FF5A00; font-weight:900; margin-top: 15px; margin-bottom: 5px; font-size: 1.6rem;'>📆 DAY {idx+1}</h3>", unsafe_allow_html=True)
            
            for slot in ["Breakfast", "Lunch", "Dinner"]:
                recipe = day_set[slot]
                st.write(f"<h5 style='color: #00A8FF; font-weight:800; margin-top: 10px; margin-bottom: 2px; font-size: 1.1rem;'>{slot.upper()}: {recipe.get('image', '🥘')} {recipe['title']}</h5>", unsafe_allow_html=True)
                
                macro_html = "".join([f"<span class='macro-badge'>{m}: {v}</span>" for m, v in recipe["macros"].items()])
                st.markdown(macro_html, unsafe_allow_html=True)
                
                clean_instructions = re.sub('<[^<]+?>', '', recipe['instructions'])
                st.markdown(f"""
                    <div class='cooking-box'>
                        <span style='color: #24140B; font-weight: bold; font-size: 0.85rem; font-family: \"League Spartan\", sans-serif;'>👩‍🍳 COOKING DIRECTIVES</span><br>
                        <p style='margin-top: 2px; font-size: 0.95rem; line-height: 1.4;'>{clean_instructions}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Save {slot} to Book", key=f"save_gen_{idx}_{slot}"):
                    already_saved = any(s['title'] == recipe['title'] for s in st.session_state.saved_links)
                    if not already_saved:
                        st.session_state.saved_links.append({
                            "title": recipe["title"],
                            "url": "AI Generated Plan",
                            "notes": f"Slot: {slot} | Macros: {recipe['macros']['Protein']} protein.",
                            "instructions": recipe["instructions"],
                            "ingredients": recipe["ingredients"]
                        })
                        st.toast(f"Added {recipe['title']}!")
                    else:
                        st.toast("Already saved!")
            st.markdown("<hr style='border-top: 1px dashed #FFE4D3; margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.write("<h3 style='color: #FF5A00; font-weight: 800;'>🛒 Step 3: Your Grocery List</h3>", unsafe_allow_html=True)
        calc_grocery = {}
        for day_set in selected_menu:
            for slot in ["Breakfast", "Lunch", "Dinner"]:
                recipe = day_set[slot]
                for ingredient, details in recipe["ingredients"].items():
                    adjusted_amount = details["amount"] * (servings / 2)
                    unit = details["unit"]
                    
                    if ingredient not in calc_grocery:
                        calc_grocery[ingredient] = {"amount": 0, "unit": unit}
                    calc_grocery[ingredient]["amount"] += adjusted_amount

        grocery_text = ""
        for ing, details in calc_grocery.items():
            am = details["amount"]
            unit_str = f" {details['unit']}" if details["unit"] else ""
            display_amount = int(am) if isinstance(am, (int, float)) and am.is_integer() else round(am, 2)
            grocery_text += f"- [ ] {display_amount}{unit_str} x {ing}\n"
            
        st.text_area(label="Copy list:", value=grocery_text, height=180, label_visibility="collapsed")

# ==========================================
# TAB 2: THE DIGITAL RECIPE BOOK
# ==========================================
with tab2:
    st.markdown("<p style='font-size: 1.1rem; font-weight: 400; color: #00A8FF !important; margin-top:5px;'>Save external discoveries or starred generator choices here.</p>", unsafe_allow_html=True)
    st.markdown("<hr style='border-top: 2px solid #FFE4D3; margin-top: 10px; margin-bottom: 15px;'>", unsafe_allow_html=True)
    
    st.write("<h3 style='color: #FF5A00; font-weight: 800;'>📥 Save a New Recipe Link</h3>", unsafe_allow_html=True)
    with st.form(key="recipe_book_form", clear_on_submit=True):
        recipe_name = st.text_input("Recipe Title")
        recipe_url = st.text_input("Link (TikTok, Insta, or Web URL)")
        recipe_notes = st.text_area("Quick Notes", height=80)
        save_button = st.form_submit_button("💾 Save to My Book")
        
    if save_button and recipe_name and recipe_url:
        st.session_state.saved_links.append({
            "title": recipe_name, 
            "url": recipe_url, 
            "notes": recipe_notes,
            "instructions": None,
            "ingredients": None
        })
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.write("<h3 style='color: #FF5A00; font-weight: 800;'>📚 My Saved Recipes</h3>", unsafe_allow_html=True)
    
    if not st.session_state.saved_links:
        st.info("Your recipe book is empty.")
    else:
        for idx, saved in enumerate(st.session_state.saved_links):
            card_col, del_col = st.columns([5, 1.2])
            with card_col:
                if "http" in saved['url']:
                    st.write(f"#### 🔗 [{saved['title']}]({saved['url']})")
                    st.caption(f"📝 {saved['notes']}")
                else:
                    st.write(f"#### 🌟 {saved['title']}")
                    st.caption(f"📝 {saved['notes']}")
                    
                    if "instructions" in saved and saved["instructions"] is not None:
                        clean_ins_book = re.sub('<[^<]+?>', '', saved["instructions"])
                        ing_text = ""
                        for ing, details in saved["ingredients"].items():
                            u_str = f" {details['unit']}" if details['unit'] else ""
                            ing_text += f"<li>{round(details['amount'], 2)}{u_str} x {ing}</li>"
                        st.markdown(f"""
                            <div class='cooking-box'>
                                <span style='color: #00A8FF; font-weight: bold; font-size: 0.85rem; font-family: \"League Spartan\", sans-serif;'>📝 INGREDIENTS</span>
                                <ul style='font-size: 0.95rem; padding-left: 20px; margin-top: 2px;'>{ing_text}</ul>
                                <span style='color: #00A8FF; font-weight: bold; font-size: 0.85rem; font-family: \"League Spartan\", sans-serif;'>👩‍🍳 DIRECTIONS</span>
                                <p style='font-size: 0.95rem; margin-top: 2px; line-height: 1.4;'>{clean_ins_book}</p>
                            </div>
                        """, unsafe_allow_html=True)
            with del_col:
                if st.button("Delete", key=f"del_{idx}", type="secondary"):
                    st.session_state.saved_links.pop(idx)
                    st.rerun()
            st.markdown("<hr style='border-top: 1px dashed #FFE4D3; margin: 10px 0;'>", unsafe_allow_html=True)

# ==========================================
# TAB 3: PAST RECIPES COOKED FEED
# ==========================================
with tab3:
    st.markdown("<p style='font-size: 1.1rem; font-weight: 400; color: #00A8FF !important; margin-top:5px;'>An automated catalog of meals herbie has cooked up for you.</p>", unsafe_allow_html=True)
    st.markdown("<hr style='border-top: 2px solid #FFE4D3; margin-top: 10px; margin-bottom: 15px;'>", unsafe_allow_html=True)
    
    st.write("<h3 style='color: #FF5A00; font-weight: 800;'>⏳ Your Cooking History</h3>", unsafe_allow_html=True)
    
    if not st.session_state.past_recipes:
        st.info("No meals have been cooked yet.")
    else:
        for idx, history_recipe in enumerate(reversed(st.session_state.past_recipes)):
            st.write(f"#### {history_recipe.get('image', '🥘')} {history_recipe['title']}")
            
            macro_html = "".join([f"<span class='macro-badge'>{m}: {v}</span>" for m, v in history_recipe["macros"].items()])
            st.markdown(macro_html, unsafe_allow_html=True)
            
            clean_ins_output = re.sub('<[^<]+?>', '', history_recipe["instructions"])
            hist_ing = ""
            for ing, details in history_recipe["ingredients"].items():
                u_str = f" {details['unit']}" if details['unit'] else ""
                hist_ing += f"<li>{round(details['amount'], 2)}{u_str} x {ing}</li>"
            st.markdown(f"""
                <div class='cooking-box' style='border-left: 4px solid #FF5A00;'>
                    <span style='color: #FF5A00; font-weight: bold; font-size: 0.85rem; font-family: \"League Spartan\", sans-serif;'>📝 INGREDIENTS REGISTER</span>
                    <ul style='font-size: 0.95rem; padding-left: 20px; margin-top: 2px;'>{hist_ing}</ul>
                    <span style='color: #FF5A00; font-weight: bold; font-size: 0.85rem; font-family: \"League Spartan\", sans-serif;'>👩‍🍳 DIRECTIONS REPLAY</span>
                    <p style='font-size: 0.95rem; margin-top: 2px; line-height: 1.4;'>{clean_ins_output}</p>
                </div>
            """, unsafe_allow_html=True)
                
            st.markdown("<hr style='border-top: 1px dashed #FFE4D3; margin: 15px 0;'>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Clear History Cache", type="secondary"):
            st.session_state.past_recipes = []
            st.rerun()