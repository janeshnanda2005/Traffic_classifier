"""Sanitize HDF5 Keras model file by replacing '/' characters in group/dataset names
and in string attributes (like 'model_config' and 'layer_names').

Usage:
    python scripts/sanitize_h5.py input.h5 output_sanitized.h5

This makes a best-effort recursive copy and replaces '/' with '_' in names and
string attributes. Always keep a backup of the original file.
"""
import sys
import h5py
import numpy as np


def sanitize_str(s: str) -> str:
    return s.replace('/', '_')


def copy_attrs(src, dst):
    for k, v in src.attrs.items():
        # Decode bytes to str if necessary
        if isinstance(v, bytes):
            try:
                s = v.decode('utf-8')
                s2 = sanitize_str(s)
                dst.attrs[k] = s2.encode('utf-8')
            except Exception:
                dst.attrs[k] = v
        elif isinstance(v, str):
            dst.attrs[k] = sanitize_str(v)
        elif isinstance(v, (list, tuple)):
            # For lists of bytes (e.g., layer_names)
            new_list = []
            changed = False
            for item in v:
                if isinstance(item, bytes):
                    try:
                        s = item.decode('utf-8')
                        s2 = sanitize_str(s)
                        new_list.append(s2.encode('utf-8'))
                        if s2 != s:
                            changed = True
                    except Exception:
                        new_list.append(item)
                elif isinstance(item, str):
                    s2 = sanitize_str(item)
                    new_list.append(s2)
                    if s2 != item:
                        changed = True
                else:
                    new_list.append(item)
            # If nothing changed, keep original
            dst.attrs[k] = new_list
        else:
            # numeric types etc.
            dst.attrs[k] = v


def copy_group(src_group, dst_group):
    # copy attributes
    copy_attrs(src_group, dst_group)

    for name, item in src_group.items():
        new_name = sanitize_str(name)
        if isinstance(item, h5py.Group):
            ng = dst_group.create_group(new_name)
            copy_group(item, ng)
        elif isinstance(item, h5py.Dataset):
            # copy dataset
            try:
                data = item[()]
                # Create dataset with same dtype
                dst_ds = dst_group.create_dataset(new_name, data=data, dtype=item.dtype)
                # copy attrs
                copy_attrs(item, dst_ds)
            except Exception:
                # For very large datasets or special objects, use low-level copy
                src_group.copy(name, dst_group, name=new_name)


def sanitize_model(input_path, output_path):
    with h5py.File(input_path, 'r') as src, h5py.File(output_path, 'w') as dst:
        copy_group(src, dst)

        # Also sanitize top-level attrs if present
        for k, v in src.attrs.items():
            if isinstance(v, bytes):
                try:
                    s = v.decode('utf-8')
                    dst.attrs[k] = sanitize_str(s).encode('utf-8')
                except Exception:
                    dst.attrs[k] = v
            elif isinstance(v, str):
                dst.attrs[k] = sanitize_str(v)
            else:
                dst.attrs[k] = v


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python scripts/sanitize_h5.py input.h5 output_sanitized.h5')
        sys.exit(2)
    inp = sys.argv[1]
    outp = sys.argv[2]
    print(f'Sanitizing {inp} -> {outp} ...')
    sanitize_model(inp, outp)
    print('Done.')
