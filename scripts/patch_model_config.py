"""Patch the model_config JSON in an HDF5 Keras model file to replace '/' with '_' in layer names.

This fixes the "Argument `name` must be a string and cannot contain character `/`" error
when loading models saved with layer names containing slashes.

Usage:
    python scripts/patch_model_config.py input.h5 output.h5
"""
import sys
import h5py
import json


def sanitize_text(text: str) -> str:
    """Replace '/' with '_' in text."""
    return text.replace('/', '_')


def patch_model_config(input_path, output_path):
    """Patch model_config attribute in HDF5 file."""
    print(f"Reading model from: {input_path}")
    
    with h5py.File(input_path, 'r') as src:
        # Read model_config attribute
        model_config = None
        if 'model_config' in src.attrs:
            raw = src.attrs['model_config']
            if isinstance(raw, bytes):
                model_config = raw.decode('utf-8')
            else:
                model_config = raw
            print(f"Found model_config attribute ({len(model_config)} chars)")
        else:
            print("ERROR: No model_config attribute found in HDF5 file")
            return False
        
        # Parse JSON and sanitize layer names
        try:
            config = json.loads(model_config)
            print(f"Parsed model config: {config.get('class_name', 'Unknown')} model")
            
            # Recursively sanitize all 'name' fields and layer references in the config
            def sanitize_config(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        # Sanitize 'name' fields (layer names)
                        if key == 'name' and isinstance(value, str):
                            obj[key] = sanitize_text(value)
                        # Sanitize inbound layer references in node connections
                        elif key == 'inbound_nodes' and isinstance(value, list):
                            for node in value:
                                if isinstance(node, list):
                                    for connection in node:
                                        if isinstance(connection, list) and len(connection) > 0:
                                            # First element is the layer name
                                            if isinstance(connection[0], str):
                                                connection[0] = sanitize_text(connection[0])
                        else:
                            sanitize_config(value)
                elif isinstance(obj, list):
                    for item in obj:
                        sanitize_config(item)
            
            sanitize_config(config)
            patched_config = json.dumps(config)
            print(f"Sanitized model_config ({len(patched_config)} chars)")
            
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse model_config as JSON: {e}")
            return False
    
    # Copy file and replace model_config attribute
    print(f"Writing patched model to: {output_path}")
    with h5py.File(input_path, 'r') as src, h5py.File(output_path, 'w') as dst:
        # Copy everything
        def copy_recursively(name, obj):
            if isinstance(obj, h5py.Group):
                src.copy(obj, dst, name=name)
        
        for name in src:
            src.copy(name, dst)
        
        # Copy root attributes
        for key, value in src.attrs.items():
            if key != 'model_config':
                dst.attrs[key] = value
        
        # Set patched model_config
        dst.attrs['model_config'] = patched_config.encode('utf-8')
    
    print("✅ Patching complete!")
    return True


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python scripts/patch_model_config.py input.h5 output.h5')
        sys.exit(2)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    success = patch_model_config(input_file, output_file)
    sys.exit(0 if success else 1)
