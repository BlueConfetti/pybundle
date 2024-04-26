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
            lines = file.read().strip().split('\n')
            patterns = []
            for line in lines:
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                # Add patterns for both directory and file matching
                patterns.append(os.path.normpath(stripped_line) + '/*')  # Directory pattern
                patterns.append(os.path.normpath(stripped_line))         # Exact file pattern
                # Include patterns with './' prefix
                patterns.append('./' + os.path.normpath(stripped_line) + '/*')  # Directory pattern with './'
                patterns.append('./' + os.path.normpath(stripped_line))         # Exact file pattern with './'
        return default_patterns + patterns
    return default_patterns


def should_ignore(path, patterns):
    # Normalize the path to remove any leading './'
    normalized_path = os.path.normpath(path)
    dot_slash_path = './' + normalized_path

    for pattern in patterns:
        if fnmatch.fnmatch(normalized_path, pattern) or fnmatch.fnmatch(dot_slash_path, pattern):
            logging.debug(f"Ignoring path {path} as it matches the pattern {pattern}")
            return True
    return False


def get_python_files_and_structure(directory, ignore_patterns):
    structure = []
    for root, dirs, files in sorted(os.walk(directory), key=lambda x: x[0]):
        dirs.sort()  # Sort directories alphabetically
        files.sort()  # Sort files alphabetically
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_patterns)]
        level = root.replace(directory, '').count(os.sep)
        indent = ' ' * 4 * level
        dir_entry = f"{indent}{os.path.basename(root)}/"
        if dir_entry not in structure:
            structure.append(dir_entry)
        subindent = ' ' * 4 * (level + 1)
        for file in files:
            if file.endswith('.py') and not should_ignore(os.path.join(root, file), ignore_patterns):
                file_path = os.path.join(root, file)
                file_entry = f"{subindent}{file}"
                if file_entry not in structure:
                    structure.append(file_entry)
                yield (structure.copy(), file_path)

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

# Retrieve both the file paths and their corresponding directory structures
all_files_and_structures = list(get_python_files_and_structure('.', ignore_patterns))
try:
    file_structure, file_paths = zip(*all_files_and_structures)  # Separate the structure and paths
    file_structure_output = '\n'.join(sum(file_structure, []))  # Flatten list

    for file_path in file_paths:
        relative_path = os.path.relpath(file_path, start='.')
        module_name = os.path.splitext(relative_path.replace(os.path.sep, '.'))[0]

        try:
            file_content = read_file_content(file_path)
        except UnicodeDecodeError as e:
            print(e)
            continue

        combined_code += f"Module: {module_name}.py\n\n{file_content}\n\n#######\n"

    output_file_path = 'concat.txt'
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        output_file.write("## File Structure\n")
        output_file.write(file_structure_output + "\n\n")
        output_file.write("## Combined Code\n")
        output_file.write(combined_code)

    num_tokens = len(encoding.encode(combined_code))
    print(f"Number of tokens: {num_tokens}")

except ValueError:
    logging.error("No Python files were found to process. Please check your directory and ignore settings.")
    # Optionally, write a message to a log file or standard output:
    print("No files found to process.")
