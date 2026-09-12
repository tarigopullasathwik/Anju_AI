import os
import py_compile
import traceback

def compile_all():
    print("Starting full syntax audit of all Python files...")
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exclude_dirs = {"venv", "venv_312", ".gemini", "__pycache__"}

    success = True
    for root, dirs, files in os.walk(root_dir):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, root_dir)
                try:
                    py_compile.compile(file_path, doraise=True)
                except py_compile.PyCompileError as e:
                    print(f"\n[ERROR] SYNTAX ERROR in: {rel_path}")
                    print(e)
                    success = False
                except Exception as e:
                    print(f"\n[ERROR] OTHER ERROR in: {rel_path}")
                    print(traceback.format_exc())
                    success = False

    if success:
        print("\n[SUCCESS] All Python files in the workspace have 100% correct syntax.")
    else:
        print("\n[FAILED] Some Python files have syntax/compilation errors.")

if __name__ == "__main__":
    compile_all()
