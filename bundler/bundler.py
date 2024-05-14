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
    
    dependencies = set()
    function_definitions = set()

    class DependencyVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_function = None
            self.local_dependencies = set()
            super().__init__()

        def visit_Import(self, node):
            for alias in node.names:
                self.local_dependencies.add(alias.name)

        def visit_ImportFrom(self, node):
            if node.module:
                self.local_dependencies.add(node.module)
                for alias in node.names:
                    self.local_dependencies.add(f"{node.module}.{alias.name}")

        def visit_FunctionDef(self, node):
            if node.name == target_function or node.name in dependencies:
                function_definitions.add(node.name)
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = None
            elif self.current_function:
                for body_item in node.body:
                    if isinstance(body_item, ast.Call):
                        if isinstance(body_item.func, ast.Name):
                            self.local_dependencies.add(body_item.func.id)
                        elif isinstance(body_item.func, ast.Attribute):
                            self.local_dependencies.add(body_item.func.attr)

        def visit_ClassDef(self, node):
            if any(attr in dependencies for attr in [node.name] + [func.name for func in node.body if isinstance(func, ast.FunctionDef)]):
                self.local_dependencies.add(node.name)
                for body_item in node.body:
                    if isinstance(body_item, ast.FunctionDef):
                        self.visit_FunctionDef(body_item)

    def get_full_dependencies(targets):
        all_dependencies = set(targets)
        for dep in list(all_dependencies):
            dep_file_path = os.path.join('.', dep.replace('.', os.sep) + '.py')
            if os.path.exists(dep_file_path):
                with open(dep_file_path, 'r', encoding='utf-8') as file:
                    node = ast.parse(file.read(), filename=dep_file_path)
                    visitor = DependencyVisitor()
                    visitor.visit(node)
                    all_dependencies.update(visitor.local_dependencies)
        return all_dependencies

    visitor = DependencyVisitor()
    visitor.visit(node)
    dependencies.update(visitor.local_dependencies)
    full_dependencies = get_full_dependencies(list(dependencies))
    return list(full_dependencies.union(function_definitions))

class FileLoader:
    def __init__(self, root_directory):
        self.root_directory = root_directory
        self.ignore_patterns = self._load_ignore_patterns()

    def _load_ignore_patterns(self):
        default_patterns = ['__pycache__/*']
        ignore_file = '.bundleignore'
        if os.path.exists(ignore_file):
            with open(ignore_file, 'r', encoding='utf-8') as file:
                lines = file.read().strip().split('\n')
                patterns = [os.path.normpath(line.strip()) for line in lines if line.strip()]
                patterns = [pattern + '/*' for pattern in patterns] + patterns
                return default_patterns + patterns
        return default_patterns

    def _should_ignore(self, path):
        normalized_path = os.path.normpath(path)
        return any(fnmatch.fnmatch(normalized_path, pattern) for pattern in self.ignore_patterns)

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
                logging.warning(f"Failed to decode {file_path} with encoding {encoding}. Trying next encoding.")
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
                current_level[dir] = {}
            current_level = current_level[dir]
        current_level[filename] = None
        
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
            try:
                module_path, function_name = target_module_function.rsplit('.', 1)
                file_path = os.path.join(self.root_directory, module_path.replace('.', os.sep) + '.py')
                dependency_list = find_function_dependencies(file_path, function_name)
                logging.info(f"Dependencies found: {dependency_list}")
                filtered_paths = []
                filtered_contents = []
                for path, content in zip(file_paths, file_contents):
                    module_name = os.path.splitext(os.path.basename(path))[0]
                    if module_name in dependency_list or any(dep in content for dep in dependency_list):
                        filtered_paths.append(path)
                        filtered_contents.append(self.filter_content(content, dependency_list))
                file_paths, file_contents = filtered_paths, filtered_contents
            except FileNotFoundError:
                logging.error(f"File not found: {file_path}")
                return

        if not file_paths:
            logging.error("No Python files were found to process. Please check your directory and ignore settings.")
            return

        structure_builder.build_structure(file_paths)
        for file_path, content in zip(file_paths, file_contents):
            relative_path = os.path.relpath(file_path, self.root_directory)
            module_name = os.path.splitext(relative_path.replace(os.path.sep, '.'))[0].lstrip(".")
            code_aggregator.add_module(module_name, content)

        self._write_output(structure_builder.tree, code_aggregator.code)
        self._calculate_tokens(code_aggregator.code)

    def filter_content(self, content, dependency_list):
        filtered_content = []
        tree = ast.parse(content)

        class ContentFilterVisitor(ast.NodeVisitor):
            def __init__(self):
                self.lines_to_include = set()

            def visit_Import(self, node):
                for alias in node.names:
                    if alias.name in dependency_list:
                        self.lines_to_include.update(range(node.lineno, node.end_lineno + 1))

            def visit_ImportFrom(self, node):
                if node.module and any(alias.name in dependency_list for alias in node.names):
                    self.lines_to_include.update(range(node.lineno, node.end_lineno + 1))

            def visit_FunctionDef(self, node):
                if node.name in dependency_list:
                    self.lines_to_include.update(range(node.lineno, node.end_lineno + 1))
                self.generic_visit(node)

            def visit_ClassDef(self, node):
                if any(attr in dependency_list for attr in [node.name] + [func.name for func in node.body if isinstance(func, ast.FunctionDef)]):
                    self.lines_to_include.update(range(node.lineno, node.end_lineno + 1))
                self.generic_visit(node)

            def visit_Expr(self, node):
                if isinstance(node.value, ast.Name) and node.value.id in dependency_list:
                    self.lines_to_include.update(range(node.lineno, node.end_lineno + 1))

            def visit_Assign(self, node):
                if any(isinstance(target, ast.Name) and target.id in dependency_list for target in node.targets):
                    self.lines_to_include.update(range(node.lineno, node.end_lineno + 1))

        visitor = ContentFilterVisitor()
        visitor.visit(tree)
        filtered_lines = [line for i, line in enumerate(content.splitlines(), 1) if i in visitor.lines_to_include]
        return "\n".join(filtered_lines)

    def _write_output(self, tree, code):
        output_file_path = 'output.txt'
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write("### ===== File Structure ===== ###\n")
            self._write_structure(tree, file)
            file.write("\n### ===== Combined Code ===== ###\n\n")
            file.write(code)

    def _write_structure(self, node, file, indent=""):
        if isinstance(node, dict):
            for key, subnode in node.items():
                if subnode is None:
                    file.write(f"{indent}{key}\n")  # This is a file
                else:
                    file.write(f"{indent}{key}/\n")  # This is a directory
                    self._write_structure(subnode, file, indent + "    ")

    def _calculate_tokens(self, code):
        num_tokens = len(self.encoding.encode(code))
        logging.info(f"Number of tokens: {num_tokens}")

def main():
    bundler = Bundler('.')  # Assuming working in the current directory
    bundler.run()

if __name__ == '__main__':
    main()