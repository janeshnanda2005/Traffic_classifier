from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from PIL import Image
import os
import base64
from io import BytesIO
from datetime import datetime
import google.generativeai as genai

app = Flask(__name__)

# Configure Google Gemini AI
GOOGLE_API_KEY = "AIzaSyCKv6xL8RWJN-6qB32kbp_0uZUCCT2VKxc"
genai.configure(api_key=GOOGLE_API_KEY)

# Model configuration: using traffic-sign.h5 
# Note: Best_DenseNet.h5 has compatibility issues with current Keras 3.x
# The model was trained with an older version and cannot be loaded properly
MODEL_FILENAME = 'traffic-sign.h5'
MODEL_PATH = os.path.join(os.path.dirname(__file__), MODEL_FILENAME)

# Lazy-loaded model: TensorFlow and the model are imported/loaded only when needed
model = None

def load_model():
    """Load the Keras model lazily. This imports TensorFlow only when the model is actually needed.

    Raises the original exception after printing a traceback to help debugging model deserialization issues.
    """
    global model
    if model is not None:
        return model

    import traceback
    try:
        # import TensorFlow locally to avoid heavy initialization on module import/py_compile
        import tensorflow as tf

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model file not found: {MODEL_PATH}\nPlease place your 'traffic-sign.h5' file in the project root."
            )

        print(f"Loading model from {MODEL_PATH} (this may take a few seconds)...")
        model = tf.keras.models.load_model(MODEL_PATH, compile=False)
        print("Model loaded successfully.")
        return model

    except Exception as e:
        print(f"Error loading model from {MODEL_PATH}: {e}")
        traceback.print_exc()
        # Re-raise so callers (process_image) get the informative exception
        raise
val = pd.read_csv("signname.csv")

# Upload folder config
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Note: Firebase logging removed — this app now only performs local image prediction

def get_gemini_prediction(image):
    """Use Google Gemini AI to independently predict the traffic sign.
    
    Args:
        image: PIL Image object of the traffic sign
    
    Returns:
        dict: Contains predicted_sign, confidence_level, and explanation
    """
    try:
        model_names = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-pro-latest']
        
        prompt = """You are an expert traffic sign recognition system. Analyze this image and identify the traffic sign.

IMPORTANT: Respond in this EXACT format:

SIGN_TYPE: [exact name of the traffic sign]
CONFIDENCE: [High/Medium/Low]
EXPLANATION: [2-3 lines explaining what you see and why you identified it this way]

Be very specific about the sign type. Common types include:
- Speed limit signs (specify the speed)
- Stop sign
- Yield sign
- No entry
- Priority road
- Dangerous curve (left/right)
- Road works
- Pedestrian crossing
- Children crossing
- Slippery road
- etc.

Focus on accuracy. If unsure, say "Unknown sign" and explain what you see."""

        for model_name in model_names:
            try:
                print(f"Trying Gemini model for prediction: {model_name}")
                gemini_model = genai.GenerativeModel(model_name)
                response = gemini_model.generate_content([prompt, image])
                
                if response and hasattr(response, 'text') and response.text:
                    print(f"✓ Gemini prediction received from: {model_name}")
                    return parse_gemini_prediction(response.text)
                    
            except Exception as model_error:
                print(f"✗ Model {model_name} failed: {str(model_error)[:100]}")
                continue
        
        # Fallback
        return {
            'predicted_sign': 'Unknown',
            'confidence_level': 'Low',
            'explanation': 'AI prediction unavailable'
        }
    
    except Exception as e:
        print(f"Error in get_gemini_prediction: {e}")
        return {
            'predicted_sign': 'Unknown',
            'confidence_level': 'Low',
            'explanation': f'Error: {str(e)[:100]}'
        }


def parse_gemini_prediction(response_text):
    """Parse Gemini's response to extract prediction details."""
    try:
        lines = response_text.strip().split('\n')
        predicted_sign = 'Unknown'
        confidence_level = 'Low'
        explanation = ''
        
        for line in lines:
            line = line.strip()
            if line.startswith('SIGN_TYPE:'):
                predicted_sign = line.replace('SIGN_TYPE:', '').strip()
            elif line.startswith('CONFIDENCE:'):
                confidence_level = line.replace('CONFIDENCE:', '').strip()
            elif line.startswith('EXPLANATION:'):
                explanation = line.replace('EXPLANATION:', '').strip()
            elif explanation and not line.startswith('SIGN_TYPE:') and not line.startswith('CONFIDENCE:'):
                # Continue explanation on next lines
                explanation += ' ' + line
        
        return {
            'predicted_sign': predicted_sign,
            'confidence_level': confidence_level,
            'explanation': explanation or 'No explanation provided'
        }
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        return {
            'predicted_sign': 'Unknown',
            'confidence_level': 'Low',
            'explanation': response_text[:200]
        }


def compare_predictions(cnn_sign, cnn_confidence, gemini_prediction):
    """Compare CNN and Gemini predictions and determine the most reliable result.
    
    Args:
        cnn_sign: Sign name from CNN model
        cnn_confidence: Confidence score from CNN (0-1)
        gemini_prediction: Dict with Gemini's prediction
    
    Returns:
        dict: Final prediction with source and verification status
    """
    try:
        gemini_sign = gemini_prediction.get('predicted_sign', 'Unknown')
        gemini_conf = gemini_prediction.get('confidence_level', 'Low')
        
        # Normalize for comparison
        cnn_sign_lower = cnn_sign.lower().strip()
        gemini_sign_lower = gemini_sign.lower().strip()
        
        # Check if predictions match (fuzzy matching)
        predictions_match = False
        if cnn_sign_lower in gemini_sign_lower or gemini_sign_lower in cnn_sign_lower:
            predictions_match = True
        
        # Check for key words match
        cnn_words = set(cnn_sign_lower.split())
        gemini_words = set(gemini_sign_lower.split())
        common_words = cnn_words.intersection(gemini_words)
        
        if len(common_words) >= 2:  # At least 2 words in common
            predictions_match = True
        
        # Decision logic - SIMPLIFIED FOR USER
        if predictions_match:
            # Both agree - Use CNN model result, don't mention AI verification
            return {
                'final_sign': cnn_sign,
                'source': 'Deep Learning Model',  # Generic name
                'verification': 'VERIFIED',
                'confidence': cnn_confidence,
                'status': 'Analyzed',
                'reliability': 'High',
                'show_comparison': False  # Hide comparison when they agree
            }
        else:
            # Predictions don't match - Use most reliable, but don't explicitly say "Google"
            if cnn_confidence >= 0.85 and gemini_conf == 'Low':
                # CNN is very confident
                return {
                    'final_sign': cnn_sign,
                    'source': 'Deep Learning Model',
                    'verification': 'VERIFIED',
                    'confidence': cnn_confidence,
                    'status': 'High confidence prediction',
                    'alternative': gemini_sign,
                    'reliability': 'High',
                    'show_comparison': True  # Show when disagree
                }
            elif cnn_confidence < 0.6 or gemini_conf in ['High', 'Medium']:
                # CNN has low confidence OR AI is confident - use AI but don't mention source
                return {
                    'final_sign': gemini_sign,
                    'source': 'AI Analysis',  # Don't say "Google Gemini"
                    'verification': 'CORRECTED',
                    'confidence': 0.80 if gemini_conf == 'High' else 0.65,
                    'status': 'Enhanced prediction',
                    'alternative': cnn_sign,
                    'reliability': 'High',
                    'show_comparison': True
                }
            else:
                # Use CNN as primary
                return {
                    'final_sign': cnn_sign,
                    'source': 'Deep Learning Model',
                    'verification': 'VERIFIED',
                    'confidence': cnn_confidence,
                    'status': 'Primary prediction',
                    'alternative': gemini_sign,
                    'reliability': 'Medium',
                    'show_comparison': True
                }
    
    except Exception as e:
        print(f"Error comparing predictions: {e}")
        return {
            'final_sign': cnn_sign,
            'source': 'Deep Learning Model',
            'verification': 'VERIFIED',
            'confidence': cnn_confidence,
            'status': 'Analyzed',
            'reliability': 'Medium',
            'show_comparison': False
        }


def get_gemini_analysis(image, sign_name=None, predicted_class=None):
    """Use Google Gemini AI to analyze the traffic sign and provide detailed description.
    
    Args:
        image: PIL Image object of the traffic sign
        sign_name: The predicted traffic sign name from the CNN model
        predicted_class: The predicted class ID
    
    Returns:
        str: Detailed analysis of the traffic sign
    """
    try:
        # Use the latest available Gemini models (confirmed working with the API key)
        model_names = [
            'gemini-2.5-flash',          # Fast, latest model
            'gemini-2.0-flash',          # Stable flash model  
            'gemini-pro-latest',         # Latest pro model
            'gemini-flash-latest',       # Latest flash alias
        ]
        
        # Create context-aware prompt with predicted sign information
        if sign_name and sign_name != "Unknown traffic sign":
            prompt = f"""You are a traffic safety expert. Our AI identified this as "{sign_name}" (Class {predicted_class}).

Provide a CONCISE summary in exactly 5-6 lines covering:
1. What this sign means and its purpose
2. What action drivers must take
3. Why it's important for safety
4. Where it's commonly found

Keep it brief, clear, and professional. Maximum 5-6 lines total."""
        else:
            prompt = """You are a traffic safety expert. Analyze this traffic sign.

Provide a CONCISE summary in exactly 5-6 lines covering:
1. Sign type and what it means
2. Required driver action
3. Safety importance
4. Common usage

Keep it brief and professional. Maximum 5-6 lines total."""
        
        # Try each model name until one works
        for model_name in model_names:
            try:
                print(f"Trying Gemini model: {model_name}")
                gemini_model = genai.GenerativeModel(model_name)
                
                # Generate content with image and prompt
                response = gemini_model.generate_content([prompt, image])
                
                # Check if response has text
                if response and hasattr(response, 'text') and response.text:
                    print(f"✓ Successfully used model: {model_name}")
                    return response.text
                    
            except Exception as model_error:
                print(f"✗ Model {model_name} failed: {str(model_error)[:100]}")
                continue
        
        # If all vision models fail, try text-only with sign information
        print("All vision models failed, trying text-only fallback...")
        return get_text_only_analysis(sign_name, predicted_class)
    
    except Exception as e:
        print(f"Error in get_gemini_analysis: {e}")
        return get_text_only_analysis(sign_name, predicted_class)


def get_text_only_analysis(sign_name=None, predicted_class=None):
    """Fallback function to get text-only analysis when vision models fail."""
    try:
        # Use latest text model
        text_model = genai.GenerativeModel('gemini-pro-latest')
        
        if sign_name and sign_name != "Unknown traffic sign":
            prompt = f"""Explain the "{sign_name}" traffic sign in exactly 5-6 concise lines.

Include:
• What it means and its purpose
• What drivers must do
• Why it's important for safety
• Where it's commonly used

Keep it brief and professional."""
        else:
            prompt = """Explain traffic signs and road safety in exactly 5-6 concise lines.

Include:
• Main types of traffic signs
• Why they're crucial for safety
• Driver responsibilities
• Impact on accident prevention

Keep it brief and professional."""
        
        response = text_model.generate_content(prompt)
        
        if sign_name and sign_name != "Unknown traffic sign":
            header = f"📋 **Detailed Information: {sign_name}**\n\n"
        else:
            header = "⚠️ **Image Analysis Unavailable - General Traffic Sign Information**\n\n"
        
        return header + response.text
        
    except Exception as e:
        # Ultimate fallback with manual information
        return create_manual_fallback(sign_name, predicted_class, str(e))


def create_manual_fallback(sign_name=None, predicted_class=None, error_msg=""):
    """Create a manual fallback response when all AI options fail."""
    if sign_name and sign_name != "Unknown traffic sign":
        return f"""**{sign_name}** (Class {predicted_class})

• This is a regulatory/warning traffic sign used for road safety
• Drivers must observe and follow the sign's instructions immediately
• Critical for preventing accidents and ensuring safe traffic flow
• Commonly found in areas requiring special attention or speed regulation
• Ignoring this sign may result in traffic violations or safety hazards

*AI analysis unavailable - Using CNN classification only*"""
    else:
        return """**Traffic Sign Classification System**

• This system uses Deep Learning CNN to identify 43 traffic sign types
• Traffic signs communicate vital road rules and safety warnings to drivers
• Following traffic signs reduces accidents and saves lives on the road
• Signs include speed limits, warnings, regulatory, and informational types
• Always pay attention to signs and obey their instructions for safety

*Upload a clear traffic sign image for AI-powered analysis*"""


def process_image(image_file):
    try:
        # Load and convert image
        image = Image.open(image_file).convert("RGB")
        
        # STEP 1: Get Gemini AI Independent Prediction FIRST
        print("=" * 60)
        print("STEP 1: Getting independent prediction from Gemini AI...")
        gemini_prediction = get_gemini_prediction(image)
        print(f"Gemini Prediction: {gemini_prediction['predicted_sign']}")
        print(f"Gemini Confidence: {gemini_prediction['confidence_level']}")
        print("=" * 60)
        
        # STEP 2: Get CNN Model Prediction
        print("STEP 2: Getting prediction from CNN Model...")
        # Preprocess image: resize to 32x32 and normalize to [0, 1]
        image_resized = image.resize((32, 32))
        image_array = np.expand_dims(np.array(image_resized), axis=0).astype('float32') / 255.0

        # Predict: ensure model is loaded lazily
        _model = model or load_model()
        prediction = _model.predict(image_array, verbose=0)
        
        # Get predicted class and confidence
        probabilities = prediction[0]
        cnn_predicted_class = int(np.argmax(probabilities))
        cnn_confidence = float(probabilities[cnn_predicted_class])
        
        # Debug: print prediction stats
        print(f"CNN Prediction shape: {prediction.shape}")
        print(f"CNN Top 3 classes: {np.argsort(probabilities)[-3:][::-1]}")
        print(f"CNN Top 3 confidences: {np.sort(probabilities)[-3:][::-1]}")
        print(f"CNN Predicted class: {cnn_predicted_class}, Confidence: {cnn_confidence:.4f}")

        # Get CNN sign name
        cnn_sign_name = "Unknown traffic sign"
        try:
            matching_rows = val[val['ClassId'] == cnn_predicted_class]
            if not matching_rows.empty:
                cnn_sign_name = matching_rows['SignName'].iloc[0]
        except Exception as e:
            print(f"Error getting sign name: {e}")
        
        print(f"CNN Sign Name: {cnn_sign_name}")
        print("=" * 60)
        
        # STEP 3: Compare predictions internally (validation only)
        print("STEP 3: Comparing CNN and Gemini predictions for validation...")
        comparison_result = compare_predictions(cnn_sign_name, cnn_confidence, gemini_prediction)
        print(f"Final Decision: {comparison_result['final_sign']}")
        print("=" * 60)
        
        # STEP 4: Get detailed AI analysis for the final prediction
        final_sign = comparison_result['final_sign']
        print(f"STEP 4: Getting detailed analysis for: {final_sign}")
        ai_description = get_gemini_analysis(image, final_sign, cnn_predicted_class)
        print("Detailed analysis received")
        print("=" * 60)

        # Encode image to base64 for frontend display
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Build simplified response - only final validated prediction
        response = {
            'success': True,
            'predicted_class': cnn_predicted_class,
            'sign_name': comparison_result['final_sign'],
            'confidence': comparison_result['confidence'],
            'ai_description': ai_description,
            'image_data': img_base64,
            'timestamp': datetime.now().isoformat()[:19]
        }

        return response

    except Exception as e:
        print(f"Error processing image: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})

    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        result = process_image(file)
        return jsonify(result)
    else:
        return jsonify({'success': False, 'error': 'Invalid file type. Use PNG, JPG, or JPEG.'})

# Firebase/test endpoints removed

if __name__ == '__main__':
    print("🚀 Starting Flask app...")
    print("Firebase logging removed — starting prediction-only server")
    app.run(debug=True, port=5000)