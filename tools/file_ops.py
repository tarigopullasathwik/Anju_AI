import os

def read_file(filepath: str, max_chars: int = 15000) -> str:
    """
    Reads the content of a file on the local system.
    Safely limits output size to prevent context overflow.
    """
    abs_path = os.path.abspath(filepath)
    if not os.path.exists(abs_path):
        return f"Error: File does not exist at '{abs_path}'."
    if os.path.isdir(abs_path):
        return f"Error: '{abs_path}' is a directory. Use list_directory to see its contents."

    try:
        # Check size first
        file_size = os.path.getsize(abs_path)
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(max_chars)

        indicator = ""
        if file_size > max_chars:
            indicator = f"\n\n[TRUNCATED: Showing first {max_chars} out of {file_size} characters]"

        return f"File Content: {abs_path}\n---\n{content}{indicator}"
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(filepath: str, content: str) -> str:
    """
    Writes content to a file, creating any parent folders automatically.
    """
    abs_path = os.path.abspath(filepath)
    try:
        # Ensure directory exists
        parent_dir = os.path.dirname(abs_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: Content written perfectly to '{abs_path}' ({len(content)} characters)."
    except Exception as e:
        return f"Error writing file: {e}"

def list_directory(directory_path: str = ".") -> str:
    """
    Lists the files and folders inside the specified directory path.
    """
    abs_path = os.path.abspath(directory_path)
    if not os.path.exists(abs_path):
        return f"Error: Directory does not exist at '{abs_path}'."
    if not os.path.isdir(abs_path):
        return f"Error: '{abs_path}' is not a directory."

    try:
        items = os.listdir(abs_path)
        dirs = []
        files = []
        for item in items:
            item_path = os.path.join(abs_path, item)
            if os.path.isdir(item_path):
                dirs.append(f"[DIR]  {item}/")
            else:
                size_kb = os.path.getsize(item_path) / 1024
                files.append(f"[FILE] {item} ({size_kb:.2f} KB)")

        output = [f"Contents of: {abs_path}\n---"]
        output.extend(sorted(dirs))
        output.extend(sorted(files))
        return "\n".join(output)
    except Exception as e:
        return f"Error listing directory: {e}"
