#!.venv/bin/python

import os
import logging
import fnmatch
import tiktoken
import argparse
import ast

logging.basicConfig(level=logging.INFO)



# At the beginning of the `if __name__ == '__main__':` block
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('target', nargs='?', help='Optional target module and function in the format module.submodule.function')
args = parser.parse_args()

# Determine if a specific target function is specified
target_module_function = args.target if args.target else None

def find_function_dependencies(file_path, target_function):
    with open(file_path, 'r', encoding='utf-8') as file:
        node = ast.parse(file.read(), filename=file_path)
    dependencies = []
    function_definitions = []

    class DependencyVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                dependencies.append(alias.name)

        def visit_ImportFrom(self, node):
            if node.module:
                dependencies.append(node.module)
                for alias in node.names:
                    dependencies.append(f"{node.module}.{alias.name}")

        def visit_FunctionDef(self, node):
            if node.name == target_function:
                function_definitions.append(node.name)
                for body_item in node.body:
                    if isinstance(body_item, ast.Call) and isinstance(body_item.func, ast.Name):
                        dependencies.append(body_item.func.id)

    visitor = DependencyVisitor()
    visitor.visit(node)
    # Combine dependencies and function_definitions for a complete list of related items
    return list(set(dependencies + function_definitions))  # Remove duplicates


class FileLoader:
    def __init__(self, root_directory):
        self.root_directory = root_directory
        self.ignore_patterns = self._load_ignore_patterns()

    def _load_ignore_patterns(self):
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
                    patterns.append(os.path.normpath(stripped_line) + '/*')
                    patterns.append(os.path.normpath(stripped_line))
                    patterns.append('./' + os.path.normpath(stripped_line) + '/*')
                    patterns.append('./' + os.path.normpath(stripped_line))
            return default_patterns + patterns
        return default_patterns

    def _should_ignore(self, path):
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.ignore_patterns)

    def get_python_files(self):
        file_paths = []
        file_contents = []
        for root, dirs, files in os.walk(self.root_directory, topdown=True):
            dirs[:] = [d for d in dirs if not self._should_ignore(os.path.join(root, d))]
            for file in files:
                if file.endswith('.py') and not self._should_ignore(os.path.join(root, file)):
                    file_path = os.path.join(root, file)
                    file_contents.append(self._read_file_content(file_path))
                    file_paths.append(file_path)
        return file_paths, file_contents

    def _read_file_content(self, file_path, encodings=['utf-8', 'latin-1', 'cp1252']):
        logging.info(f"Reading file: {file_path}")
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError(f"Failed to decode {file_path} with any of the provided encodings.")
    
class StructureBuilder:
    def __init__(self):
        self.tree = {}

    def build_structure(self, file_paths):
        for file_path in file_paths:
            relative_path = os.path.relpath(file_path, '.')
            dirs, filename = os.path.split(relative_path)
            self._add_file_to_tree(dirs, filename)

    def _add_file_to_tree(self, dirs, filename):
        current_level = self.tree
        for dir in dirs.split(os.sep):
            if dir not in current_level:
                current_level[dir] = []
            current_level = current_level[dir]
        current_level.append(filename)
        
        
class CodeAggregator:
    def __init__(self):
        self.code = ""

    def add_module(self, module_name, content):
        self.code += f"Module: {module_name}.py\n\n{content}\n\n#######\n"

class Bundler:
    def __init__(self, root_directory):
        self.root_directory = root_directory
        self.encoding = tiktoken.encoding_for_model("gpt-4")

    def run(self):
        structure_builder = StructureBuilder()
        code_aggregator = CodeAggregator()

        file_loader = FileLoader(self.root_directory)
        file_paths, file_contents = file_loader.get_python_files()

        if target_module_function:
            module_path, function_name = target_module_function.rsplit('.', 1)
            file_path = os.path.join(self.root_directory, module_path.replace('.', os.sep) + '.py')
            try:
                dependency_list = find_function_dependencies(file_path, function_name)
                print(f"Dependencies found: {dependency_list}")  # Debugging line to see what's found
                filtered_paths = []
                filtered_contents = []
                for path, content in zip(file_paths, file_contents):
                    basename = os.path.splitext(os.path.basename(path))[0]
                    if basename in dependency_list or any(dep in content for dep in dependency_list):
                        filtered_paths.append(path)
                        filtered_contents.append(content)
                file_paths, file_contents = filtered_paths, filtered_contents
            except FileNotFoundError:
                logging.error(f"File not found: {file_path}")
                return
        if not file_paths:
            logging.error("No Python files were found to process. Please check your directory and ignore settings.")
            return  # Exit the method if no files are found to avoid further processing.

        structure_builder.build_structure(file_paths)

        for file_path, content in zip(file_paths, file_contents):
            relative_path = os.path.relpath(file_path, self.root_directory)
            module_name = os.path.splitext(relative_path.replace(os.path.sep, '.'))[0].lstrip(".")
            code_aggregator.add_module(module_name, content)

        self._write_output(structure_builder.tree, code_aggregator.code)
        self._calculate_tokens(code_aggregator.code)

    def _write_output(self, tree, code):
        output_file_path = 'output.txt'
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write("## File Structure\n")
            self._write_structure(tree, file)
            file.write("\n## Combined Code\n")
            file.write(code)

    def _write_structure(self, node, file, indent=""):
        if isinstance(node, dict):
            for key, subnode in node.items():
                file.write(f"{indent}{key}/\n")
                self._write_structure(subnode, file, indent + "    ")
        else:
            for filename in node:
                file.write(f"{indent}{filename}\n")

    def _calculate_tokens(self, code):
        num_tokens = len(self.encoding.encode(code))
        print(f"Number of tokens: {num_tokens}")
        
if __name__ == '__main__':
    bundler = Bundler('.')  # Assuming working in the current directory
    bundler.run()