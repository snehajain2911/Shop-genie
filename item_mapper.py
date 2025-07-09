from pymongo import MongoClient
import random  # For generating random prices

MONGO_URI = "mongodb+srv://abhidhanroy02072004:abhi1234@storedb.caiu1s9.mongodb.net/store_db?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['store_db']
collection = db['products']

def get_items_for_keywords(items, budget, location, quantity):
    matched_items = []

    if not items:
        print("⚠️ No items extracted. Using fallback.")
        items = ['rice']

    for keyword in items:
        query = {
            "product_name": {"$regex": keyword, "$options": "i"}
        }

        if location.lower() != 'any' and location.strip():
            query["location"] = {"$regex": location, "$options": "i"}

        print(f"🔍 Querying MongoDB for: {keyword}")
        print("🧾 Full query:", query)

        try:
            cursor = collection.find(query)
            count = 0

            for product in cursor:
                count += 1
                print("✅ Found:", product.get("product_name"))

                # Assign random price between ₹50 and ₹300
                random_price = random.randint(50, 300)

                matched_items.append({
                    "name": product.get("product_name", "Unnamed"),
                    "product_id": product.get("product_id", ""),
                    "quantity_available": product.get("qty", 0),
                    "location": product.get("location", "Unknown"),
                    "rack": product.get("rack", "Unknown"),
                    "floor": product.get("floor", "Unknown"),
                    "price": random_price
                })

            print(f"🔢 {count} item(s) matched for keyword: {keyword}")

        except Exception as e:
            print(f"❌ Error querying for {keyword}:", e)

    if not matched_items:
        print("❌ No items matched at all.")

    return matched_items
