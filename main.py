import io
import time
from flask import Flask, render_template, request, jsonify
from google import genai
from PIL import Image

app = Flask(__name__)

# Direct API Key initialization
try:
    client = genai.Client(api_key="AQ.Ab8RN6LanmXuSnyY80T59ZoDQqDKMPWf4ai7A4xzYOUuNtXeLA")
except Exception as e:
    print(f"Initialization Error: {e}")
    client = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_image():
    if not client:
        return jsonify({'error': 'Gemini Client is not active.'}), 500

    if 'image' not in request.files:
        return jsonify({'error': 'No asset payload matched standard boundary headers'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))

        prompt = (
            "You are a professional image classification engine. Identify all individual items "
            "and materials present inside the frame. Return a clean, structural itemized bulleted list "
            "with precise structural context, approximate placement notes, or visual highlights."
        )

        # Robust Retry Loop to combat 503 "High Demand" Server Errors
        max_retries = 3
        delay = 2  # Start with a 2-second delay
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[image, prompt]
                )
                # If successful, return immediately
                return jsonify({'result': response.text})
                
            except Exception as e:
                error_msg = str(e)
                # If it's a 503/high-demand error, wait and retry
                if "503" in error_msg or "high demand" in error_msg.lower():
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 1.5  # Increase wait time slightly for the next attempt
                        continue
                
                # If it's any other error, or we ran out of retries, raise it to be caught below
                raise e

    except Exception as e:
        error_msg = str(e)
        # Friendly message for the user UI if the server is absolutely stuck
        if "503" in error_msg or "high demand" in error_msg.lower():
            return jsonify({'error': 'The AI engine is experiencing heavy public traffic. Please wait a moment and try again.'}), 503
        return jsonify({'error': error_msg}), 500

# Run Application
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',   # Allow external connections
        port=5000,        # Port number
        debug=True        # Development mode
    )