import os

def ensure_dir(path):
    """
    Ensure the directory at `path` exists. If not, create it.
    """
    if not os.path.exists(path):
        os.makedirs(path)
