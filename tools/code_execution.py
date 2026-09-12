import subprocess
import tempfile
import os
import sys
import time

def execute_python_code(code: str, timeout: int = 15) -> str:
    """
    Executes a block of Python code in a secure subprocess.
    Returns the execution logs, printed stdout, and errors.
    """
    # Create a temporary file to hold the code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code)
        temp_path = temp_file.name

    try:
        start_time = time.time()
        # Execute the python script
        result = subprocess.run(
            [sys.executable, temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        elapsed = time.time() - start_time

        output = []
        if result.stdout:
            output.append(f"--- Standard Output ---\n{result.stdout}")
        if result.stderr:
            output.append(f"--- Standard Error (Diagnostic) ---\n{result.stderr}")

        output.append(f"Execution completed in {elapsed:.3f} seconds with exit code {result.returncode}.")
        return "\n\n".join(output)

    except subprocess.TimeoutExpired:
        return f"Error: Execution timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing Python block: {e}"
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

def execute_terminal_command(command: str, timeout: int = 15) -> str:
    """
    Executes a shell command (PowerShell on Windows) and returns stdout/stderr.
    """
    try:
        start_time = time.time()
        # Use shell execution
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        elapsed = time.time() - start_time

        output = []
        if result.stdout:
            output.append(f"--- Standard Output ---\n{result.stdout}")
        if result.stderr:
            output.append(f"--- Standard Error ---\n{result.stderr}")

        output.append(f"Command completed in {elapsed:.3f} seconds with exit code {result.returncode}.")
        return "\n\n".join(output)

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing terminal command: {e}"
