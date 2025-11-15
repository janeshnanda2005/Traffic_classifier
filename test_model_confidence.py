#!/usr/bin/env python3
"""
Test script to check model predictions and confidence values
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf
import numpy as np
from PIL import Image
import sys

def test_model_predictions(model_path, image_path):
    """Test model predictions and analyze confidence values"""
    
    print(f"\n{'='*60}")
    print(f"Testing model: {model_path}")
    print(f"{'='*60}\n")
    
    # Load model
    print("Loading model...")
    model = tf.keras.models.load_model(model_path, compile=False)
    print(f"✅ Model loaded")
    print(f"   Input shape: {model.input_shape}")
    print(f"   Output shape: {model.output_shape}")
    
    # Check last layer activation
    last_layer = model.layers[-1]
    print(f"\n   Last layer: {last_layer.name}")
    print(f"   Last layer type: {type(last_layer).__name__}")
    if hasattr(last_layer, 'activation'):
        print(f"   Activation: {last_layer.activation.__name__}")
    
    # Load and preprocess image
    print(f"\nLoading image: {image_path}")
    image = Image.open(image_path).convert("RGB")
    print(f"   Original size: {image.size}")
    
    image_resized = image.resize((32, 32))
    image_array = np.expand_dims(np.array(image_resized), axis=0)
    print(f"   Input array shape: {image_array.shape}")
    print(f"   Input array dtype: {image_array.dtype}")
    print(f"   Input array range: [{image_array.min()}, {image_array.max()}]")
    
    # Normalize if needed (most models expect 0-1 range)
    if image_array.max() > 1.0:
        image_array_normalized = image_array.astype('float32') / 255.0
        print(f"   Normalized range: [{image_array_normalized.min():.3f}, {image_array_normalized.max():.3f}]")
    else:
        image_array_normalized = image_array
    
    # Make predictions with both normalized and non-normalized inputs
    print(f"\n{'='*60}")
    print("Testing predictions:")
    print(f"{'='*60}\n")
    
    for name, arr in [("Original (0-255)", image_array), ("Normalized (0-1)", image_array_normalized)]:
        print(f"\n{name}:")
        prediction = model.predict(arr, verbose=0)
        probabilities = prediction[0]
        
        print(f"   Prediction shape: {prediction.shape}")
        print(f"   Sum of probabilities: {probabilities.sum():.6f}")
        print(f"   Min probability: {probabilities.min():.6f}")
        print(f"   Max probability: {probabilities.max():.6f}")
        
        # Get top 5 predictions
        top_5_indices = np.argsort(probabilities)[-5:][::-1]
        print(f"\n   Top 5 predictions:")
        for i, idx in enumerate(top_5_indices, 1):
            print(f"   {i}. Class {idx}: {probabilities[idx]:.6f} ({probabilities[idx]*100:.2f}%)")
    
    print(f"\n{'='*60}")
    print("Analysis:")
    print(f"{'='*60}\n")
    
    # Check if probabilities sum to 1 (softmax output)
    if abs(probabilities.sum() - 1.0) < 0.01:
        print("✅ Model has softmax output (probabilities sum to ~1.0)")
        print("   Confidence values should be between 0 and 1")
    else:
        print("⚠️  Model might not have softmax output")
        print(f"   Probabilities sum to {probabilities.sum():.6f}")
        print("   You may need to apply softmax manually")
    
    print()

if __name__ == "__main__":
    # Test with traffic-sign.h5
    model_path = "traffic-sign.h5"
    
    # Use a test image
    test_images = [
        "tests/speed-limit-sign-30-km-h.jpg",
        "tests/traffic-arrow-sign-only-left_23-2148445334.png"
    ]
    
    for img_path in test_images:
        if os.path.exists(img_path):
            test_model_predictions(model_path, img_path)
            break
    else:
        print("No test images found!")
        print("Please provide an image path as argument:")
        print(f"  python {sys.argv[0]} path/to/image.jpg")
