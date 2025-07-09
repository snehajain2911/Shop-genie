import google.generativeai as genai
from dotenv import load_dotenv
import os
# Load environment variables
load_dotenv()

# Get Gemini API key
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=gemini_api_key)
# ✅ Load the Gemini model
model = genai.GenerativeModel(model_name="gemini-2.5-pro")

# ✅ Few-shot prompt template
def extract_items(user_input):
    prompt = f"""
You are a smart shopping assistant. Convert the user's request into structured shopping data.

Format: items=[item1, item2]; budget=amount; quantity=number; location=location

Examples:
1. Input: I need rice and oil for 2 people under 500
   → items=[rice, oil]; budget=500; quantity=2; location=any

2. Input: I want a healthy salad under 500
   → items=[lettuce, cucumber, tomato, olive oil]; budget=500; quantity=1; location=any

3. Input: Get me detergent and mop from Aisle 2
   → items=[detergent, mop]; budget=1000; quantity=1; location=Aisle 2

Now convert this:
Input: {user_input}
→
"""

    try:
        response = model.generate_content(prompt)
        output = response.text.strip()
        print("\n🧠 Gemini Output:", output)

        # Parse key=value pairs
        info = {}
        for part in output.split(';'):
            if '=' in part:
                key, value = part.strip().split('=')
                info[key.strip()] = value.strip().strip('[]')

        return {
            'items': [x.strip() for x in info.get('items', '').split(',') if x.strip()],
            'budget': int(info.get('budget', 1000)),
            'location': info.get('location', 'any'),
            'quantity': int(info.get('quantity', 1))
        }

    except Exception as e:
        print("❌ Error parsing Gemini output:", e)
        return {
            'items': [],
            'budget': 1000,
            'location': 'any',
            'quantity': 1
        }
