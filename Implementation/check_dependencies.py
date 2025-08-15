# check_dependencies.py
# Run this in your Implementation folder to see what you actually import

import os
import re
import ast

def find_imports_in_file(filepath):
    """Extract all imports from a Python file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add(name.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        
        return imports
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return set()

def find_all_python_files(directory):
    """Find all Python files in directory"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ and .venv directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.venv', 'venv', '.git']]
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def main():
    # Get current directory (should be Implementation folder)
    current_dir = os.getcwd()
    print(f"Scanning Python files in: {current_dir}")
    
    all_imports = set()
    python_files = find_all_python_files(current_dir)
    
    print(f"\nFound {len(python_files)} Python files:")
    for file in python_files:
        rel_path = os.path.relpath(file, current_dir)
        print(f"  {rel_path}")
        file_imports = find_imports_in_file(file)
        all_imports.update(file_imports)
    
    # Filter out standard library and local imports
    external_imports = set()
    stdlib_modules = {
        'os', 'sys', 'json', 'time', 'datetime', 'logging', 'pathlib', 'typing',
        'collections', 'itertools', 'functools', 're', 'math', 'random', 'uuid',
        'asyncio', 'concurrent', 'threading', 'multiprocessing', 'pickle', 'csv',
        'io', 'contextlib', 'warnings', 'traceback', 'inspect', 'copy', 'operator'
    }
    
    local_modules = {'config', 'chatbot', 'embedding', 'search', 'llm_integration', 
                     'admin_api', 'file_processor', 'chromadb_manager', 'app'}
    
    for imp in all_imports:
        if imp not in stdlib_modules and imp not in local_modules:
            external_imports.add(imp)
    
    print(f"\n🔍 External dependencies found:")
    for imp in sorted(external_imports):
        print(f"  {imp}")
    
    print(f"\n📦 Suggested requirements.txt based on your imports:")
    
    # Map common import names to package names
    package_mapping = {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn[standard]',
        'pydantic': 'pydantic',
        'sentence_transformers': 'sentence-transformers',
        'mistralai': 'mistralai',
        'chromadb': 'chromadb',
        'numpy': 'numpy',
        'sklearn': 'scikit-learn',
        'dotenv': 'python-dotenv',
        'aiofiles': 'aiofiles',
        'jinja2': 'jinja2',
        'httpx': 'httpx',
        'orjson': 'orjson',
        'multipart': 'python-multipart'
    }
    
    for imp in sorted(external_imports):
        package_name = package_mapping.get(imp, imp)
        print(f"{package_name}")

if __name__ == "__main__":
    main()