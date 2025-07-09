import qrcode
import io
from PIL import Image

def generate_qr(items):
    data = "\n".join([f"{item['name']} (₹{item['final_cost']}) - Aisle: {item['location']}, Rack: {item['rack']}" for item in items])
    qr = qrcode.make(data)
    buffered = io.BytesIO()
    qr.save(buffered, format="PNG")
    buffered.seek(0)
    return Image.open(buffered)
