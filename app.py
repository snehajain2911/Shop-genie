import streamlit as st
from extractor import extract_items
from item_mapper import get_items_for_keywords
from pymongo import MongoClient
from PIL import Image, ImageDraw
import json
import random
import re
import io
import os
import tempfile
from fpdf import FPDF
import qrcode

# === MongoDB Setup ===
from dotenv import load_dotenv
import os

# === MongoDB Setup ===
# Load environment variables
load_dotenv()

# Get MongoDB URI
mongo_uri = os.getenv("uri")
client = MongoClient(mongo_uri)
db = client["store_db"]
products_col = db["products"]

# === Load Aisle Coordinates ===
with open("aisle_coords.json", "r") as f:
    AISLE_POSITIONS = json.load(f)

# === Load Store Map and Marker Icon ===
MAP_PATH = "store_map.png"
MARKER_PATH = "marker.png"
base_map = Image.open(MAP_PATH).convert("RGBA")
try:
    marker_img = Image.open(MARKER_PATH).resize((40, 40)).convert("RGBA")
except:
    marker_img = None

# === Aisle Color Generator ===
AISLE_COLORS = {}
def get_color_for_aisle(aisle):
    if aisle not in AISLE_COLORS:
        AISLE_COLORS[aisle] = tuple(random.randint(50, 200) for _ in range(3)) + (180,)
    return AISLE_COLORS[aisle]

# === Unicode PDF Support ===
class UnicodePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        self.set_font('DejaVu', '', 12)

def generate_pdf(selected_products, parsed_info, total_price, map_image):
    pdf = UnicodePDF()
    pdf.add_page()

    pdf.cell(200, 10, txt="🛒 Smart Shop Assistant Summary", ln=True, align="C")
    pdf.ln(5)

    pdf.cell(200, 10, txt=f"🧺 Items: {', '.join(parsed_info['items'])}", ln=True)
    pdf.cell(200, 10, txt=f"💰 Budget: ₹{parsed_info['budget']}", ln=True)
    pdf.cell(200, 10, txt=f"📍 Aisle Preference: {parsed_info['location']}", ln=True)
    pdf.cell(200, 10, txt=f"👥 Quantity: {parsed_info['quantity']}", ln=True)
    pdf.cell(200, 10, txt=f"💵 Total Estimated Cost: ₹{total_price}", ln=True)

    pdf.ln(5)
    pdf.cell(200, 10, txt="🛍️ Products:", ln=True)

    for product in selected_products:
        pdf.multi_cell(0, 10, txt=(
            f"🛍️ {product['name']}\n"
            f"Product ID: {product['product_id']}\n"
            f"Aisle: {product['location']} | Rack: {product['rack']} | Floor: {product['floor']}\n"
            f"Quantity: {product['final_qty']} | Cost: ₹{product['final_cost']}\n"
        ), border=1)
        pdf.ln(2)

    temp_map = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    map_image.save(temp_map.name)
    pdf.image(temp_map.name, x=10, y=None, w=180)
    temp_map.close()

    pdf_path = os.path.join(tempfile.gettempdir(), "shopping_summary.pdf")
    pdf.output(pdf_path)

    return pdf_path

def generate_qr_from_url(url):
    qr = qrcode.make(url)
    buffered = io.BytesIO()
    qr.save(buffered, format="PNG")
    buffered.seek(0)
    return Image.open(buffered)

# === Streamlit UI Setup ===
st.set_page_config(page_title="Smart Shop Assistant + Map", layout="wide")
st.title("🛒 Smart Shop Assistant + Aisle Map")
st.write("Describe your shopping need, get smart suggestions, and see items visually on the store map.")

user_input = st.text_input("📝 What do you need?", placeholder="e.g., I want chips and juice under 200 from Aisle 5")

if user_input:
    with st.spinner("🧠 Understanding your need..."):
        parsed_info = extract_items(user_input)

        if parsed_info['quantity'] == 1:
            match = re.search(r'(\d+)\s*(kids|people|persons|students|guests)', user_input.lower())
            if match:
                parsed_info['quantity'] = int(match.group(1))

        st.subheader("🔍 Extracted Summary")
        st.markdown(f"""
        - **🧺 Items Requested:** {', '.join(parsed_info['items']) or 'Not found'}
        - **💰 Budget:** ₹{parsed_info['budget']}
        - **📍 Aisle Preference:** {parsed_info['location']}
        - **👥 Quantity:** {parsed_info['quantity']}
        """)

        items = get_items_for_keywords(
            items=parsed_info['items'],
            budget=parsed_info['budget'],
            location=parsed_info['location'],
            quantity=parsed_info['quantity']
        )

        if not items:
            st.warning("No items found for your criteria.")
        else:
            total_price = 0
            selected_products = []
            coords = []

            st.subheader("✅ Recommended Items")

            for i, item in enumerate(items, start=1):
                quantity_requested = parsed_info['quantity']
                name = item.get('name', '').lower()

                if "balloon" in name or "snack" in name or "drink" in name or "juice" in name:
                    qty = quantity_requested
                elif "cake" in name:
                    qty = 1
                else:
                    qty = max(1, quantity_requested // 2)

                item_price = item.get('price', 100)
                cost = qty * item_price
                total_price += cost

                selected_products.append({
                    **item,
                    "final_qty": qty,
                    "final_cost": cost
                })

                st.markdown(f"""
                <div style='border: 1px solid #ddd; border-radius: 10px; padding: 10px; margin-bottom: 10px; background-color: #f9f9f9;'>
                    <b>🛍️ {item.get('name', 'Unnamed')}</b><br>
                    🧾 Product ID: {item.get('product_id', 'N/A')}<br>
                    📦 Quantity: {qty}<br>
                    🗂️ Aisle: {item.get('location')} | Rack: {item.get('rack')} | Floor: {item.get('floor')}<br>
                    💰 Cost: ₹{cost}
                </div>
                """, unsafe_allow_html=True)

                aisle_key = item.get('location')
                if aisle_key in AISLE_POSITIONS:
                    try:
                        x, y = AISLE_POSITIONS[aisle_key]
                        coords.append((int(x), int(y)))
                    except Exception as e:
                        print(f"❌ Invalid coordinates for '{aisle_key}': {e}")

            st.success(f"💵 Total Estimated Cost: ₹{total_price}")

            st.subheader("📜 Store Map with Product Locations")
            map_copy = base_map.copy()
            draw = ImageDraw.Draw(map_copy)

            if len(coords) >= 2 and all(isinstance(c, tuple) and len(c) == 2 and all(isinstance(i, int) for i in c) for c in coords):
                draw.line(coords, fill=(0, 100, 255, 255), width=6)

            for product in selected_products:
                aisle_key = product.get('location')
                if aisle_key not in AISLE_POSITIONS:
                    continue
                x, y = AISLE_POSITIONS[aisle_key]
                color = get_color_for_aisle(aisle_key)

                if marker_img:
                    map_copy.paste(marker_img, (x - 20, y - 40), marker_img)
                else:
                    r = 20
                    draw.ellipse((x - r, y - r, x + r, y + r), fill=color, outline="white", width=3)

            buf = io.BytesIO()
            resized_map = map_copy.resize((int(727 * (399 / 727)), 600))
            resized_map.save(buf, format="PNG")
            st.image(buf.getvalue(), caption="🧽 Items on Store Map")

            # === Interactive Aisle Legend ===
            st.subheader("📍 Aisle Legend with Products")
            if "aisle_visibility" not in st.session_state:
                st.session_state.aisle_visibility = {aisle: True for aisle in AISLE_COLORS}

            aisle_products = {}
            for product in selected_products:
                aisle = product['location']
                name = product['name']
                if aisle not in aisle_products:
                    aisle_products[aisle] = []
                aisle_products[aisle].append(name)

            for aisle, color in AISLE_COLORS.items():
                hex_color = '#%02x%02x%02x' % color[:3]
                default = st.session_state.aisle_visibility.get(aisle, True)
                st.session_state.aisle_visibility[aisle] = st.checkbox(
                    f"🟢 Aisle {aisle} - {', '.join(aisle_products.get(aisle, [])) or 'No products'}",
                    value=default,
                    key=f"checkbox_{aisle}"
                )

            # === Generate PDF and QR ===
            pdf_path = generate_pdf(selected_products, parsed_info, total_price, map_copy)
            st.subheader("📄 Download Your Shopping Summary")
            with open(pdf_path, "rb") as f:
                st.download_button(label="⬇️ Download PDF", data=f, file_name="shopping_summary.pdf", mime="application/pdf")

            pdf_url = "http://localhost:8501/shopping_summary.pdf"
            qr_img = generate_qr_from_url(pdf_url)
            st.image(qr_img.resize((300, 300)), caption="📱 Scan to View PDF on Mobile")
