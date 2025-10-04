import os


def create_dir(dir: str):
    if not os.path.exists(dir):
        # If it doesn't exist, create the directory
        os.makedirs(dir)
        print(f"Directory {dir} created.")
