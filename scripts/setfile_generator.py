import os

def save_setfile(setfile_path, params_dict):
    """
    Save a .set file in proper UTF-16 LE with BOM format for MT5 Strategy Tester.

    Args:
        setfile_path (str): Full path to save the .set file.
        params_dict (dict): Dictionary of EA inputs and values.
    """
    lines = ["[Common]\n"]
    for k, v in params_dict.items():
        if isinstance(v, bool):
            v = int(v)
        lines.append(f"{k}={v}\n")

    content = ''.join(lines)

    # Save in UTF-16 LE with BOM for MT5 compatibility
    with open(setfile_path, 'wb') as f:
        f.write(b'\xff\xfe')  # UTF-16 LE BOM
        f.write(content.encode('utf-16le'))

    return setfile_path
