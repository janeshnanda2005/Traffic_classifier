# Best_DenseNet.h5 Compatibility Issue

## Problem

The `Best_DenseNet.h5` model cannot be loaded with current Keras/TensorFlow versions due to layer naming incompatibility.

**Error:**
```
TypeError: Error when deserializing class 'Conv2D' using config={'name': 'conv1/conv', ...}
Exception encountered: Argument `name` must be a string and cannot contain character `/`.
Received: name=conv1/conv
```

## Root Cause

The model was saved with layer names containing forward slashes (`/`), which are no longer allowed in newer versions of Keras (Keras 3.x / TensorFlow 2.13+).

Layer names like:
- `conv1/conv`
- `bn1/gamma`
- `pool1/pool`

These were valid in older TensorFlow/Keras versions but are now invalid.

## Solutions

### Option 1: Use traffic-sign.h5 (RECOMMENDED - Currently Active)

The `traffic-sign.h5` model works perfectly with the current setup.

**Status:** ✅ Working
**File:** `app.py` is currently configured to use this model

```python
MODEL_FILENAME = 'traffic-sign.h5'
```

### Option 2: Fix the Best_DenseNet.h5 Model

To use Best_DenseNet.h5, you need to:

#### A. Downgrade TensorFlow/Keras (Not Recommended)

```bash
pip install tensorflow==2.10.0
```

This is not recommended as it uses older, potentially less secure versions.

#### B. Convert the Model Architecture (Advanced)

1. Load the model in an environment with TensorFlow 2.10 or earlier
2. Extract the architecture and weights
3. Recreate with compatible layer names
4. Save the new model

**Script to convert (requires TensorFlow 2.10):**

```python
# Run this in Python 3.9 with TensorFlow 2.10
import tensorflow as tf

# Load old model
old_model = tf.keras.models.load_model('Best_DenseNet.h5')

# Get architecture config
config = old_model.get_config()

# Function to sanitize layer names
def sanitize_config(config):
    if isinstance(config, dict):
        if 'name' in config and isinstance(config['name'], str):
            config['name'] = config['name'].replace('/', '_')
        for key, value in config.items():
            config[key] = sanitize_config(value)
    elif isinstance(config, list):
        return [sanitize_config(item) for item in config]
    return config

# Sanitize configuration
new_config = sanitize_config(config)

# Create new model from sanitized config
new_model = tf.keras.Model.from_config(new_config)

# Copy weights
new_model.set_weights(old_model.get_weights())

# Save with compatible layer names
new_model.save('Best_DenseNet_fixed.h5')
print("Model saved as Best_DenseNet_fixed.h5")
```

#### C. Use Model Weights Only

Extract weights and load into a fresh DenseNet architecture:

```python
from tensorflow.keras.applications import DenseNet121

# Create base model
base_model = DenseNet121(
    include_top=False,
    weights=None,
    input_shape=(32, 32, 3)
)

# Add custom top layers to match your model
x = base_model.output
x = tf.keras.layers.GlobalAveragePooling2D()(x)
x = tf.keras.layers.Dense(256, activation='relu')(x)
predictions = tf.keras.layers.Dense(43, activation='softmax')(x)

model = tf.keras.Model(inputs=base_model.input, outputs=predictions)

# Load weights from old model (this may work if architecture matches)
try:
    model.load_weights('Best_DenseNet.h5', by_name=True, skip_mismatch=True)
    print("Weights loaded successfully")
except Exception as e:
    print(f"Could not load weights: {e}")

# Save new model
model.save('DenseNet_compatible.h5')
```

## Current Configuration

**Active Model:** `traffic-sign.h5` ✅

To check which model is being used:

```bash
cd /home/mahemano/Desktop/innovation_projects/INTERN/Traffic_classifier
grep "MODEL_FILENAME" app.py
```

## Recommendation

**Continue using `traffic-sign.h5`** - it works perfectly and provides good accuracy for traffic sign classification. The model is smaller (8.1 MB vs 324 MB) and loads faster.

If you specifically need the DenseNet architecture's performance:
1. Use a separate environment with TensorFlow 2.10
2. Convert the model using Option 2B above
3. Test the converted model
4. Deploy the fixed version

## Files

- ✅ `traffic-sign.h5` - 8.1 MB - **WORKING**
- ❌ `Best_DenseNet.h5` - 324 MB - **INCOMPATIBLE**
- ❌ `Best_DenseNet_fixed.h5` - 324 MB - **INCOMPATIBLE**
- ❌ `Best_DenseNet_sanitized.h5` - 324 MB - **INCOMPATIBLE**

## Testing

Test if your model loads:

```bash
cd /home/mahemano/Desktop/innovation_projects/INTERN/Traffic_classifier
source env/bin/activate
python3 -c "
import tensorflow as tf
model = tf.keras.models.load_model('traffic-sign.h5', compile=False)
print('✅ Model loaded successfully!')
print(f'Input: {model.input_shape}, Output: {model.output_shape}')
"
```

---

**Last Updated:** November 8, 2025
**Status:** Using traffic-sign.h5 model (working)
