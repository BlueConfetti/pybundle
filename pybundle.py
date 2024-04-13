#!.venv/bin/python

import os
import tiktoken
import fnmatch
import logging

logging.basicConfig(level=logging.INFO)

encoding = tiktoken.encoding_for_model("gpt-4")

def read_ignore_patterns():
    default_patterns = ['__pycache__/*']  # Default patterns to ignore
    ignore_file = '.bundleignore'
    if os.path.exists(ignore_file):
        with open(ignore_file, 'r', encoding='utf-8') as file:
            patterns = file.read().strip().split('\n')
        return default_patterns + patterns
    return default_patterns

def should_ignore(path, patterns):
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)

def get_python_files(directory, ignore_patterns):
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_patterns)]
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith('.py') and not should_ignore(file_path, ignore_patterns):
                yield file_path

def read_file_content(file_path, encodings=['utf-8', 'latin-1', 'cp1252']):
    logging.info(f"Reading file: {file_path}")
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Failed to decode {file_path} with any of the provided encodings.")

ignore_patterns = read_ignore_patterns()
combined_code = ""
file_paths = list(get_python_files('.', ignore_patterns))

for file_path in file_paths:
    relative_path = os.path.relpath(file_path, start='.')
    module_name = relative_path.replace(os.path.sep, '.').rstrip('.py')
    if module_name == 'pybundle':
        continue

    try:
        file_content = read_file_content(file_path)
    except UnicodeDecodeError as e:
        print(e)
        continue

    combined_code += f"Module: {module_name}.py\n\n{file_content}\n\n#######\n"

output_file_path = 'concat.txt'
with open(output_file_path, 'w', encoding='utf-8') as output_file:
    output_file.write(combined_code)

num_tokens = len(encoding.encode(combined_code))
print(f"Number of tokens: {num_tokens}")
