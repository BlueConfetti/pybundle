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

    import_aliases = {}
    dependencies = set()
    visited_functions = set()
    call_graph = {}  # Key: function, Value: set of called functions

    # Collect all function definitions and import aliases
    class DefinitionCollector(ast.NodeVisitor):
        def __init__(self):
            super().__init__()
            self.function_defs = {}

        def visit_FunctionDef(self, node):
            self.function_defs[node.name] = node
            self.generic_visit(node)

        def visit_Import(self, node):
            for alias in node.names:
                import_aliases[alias.asname or alias.name] = alias.name

        def visit_ImportFrom(self, node):
            if node.module:
                for alias in node.names:
                    import_aliases[alias.asname or alias.name] = node.module

    collector = DefinitionCollector()
    collector.visit(node)
    function_defs = collector.function_defs

    def visit_function(function_name, module_name=None):
        key = (module_name, function_name)
        if key in visited_functions:
            return
        visited_functions.add(key)

        if module_name is None:
            function_node = function_defs.get(function_name)
            if not function_node:
                return
        else:
            module_file = os.path.join('.', module_name.replace('.', os.sep) + '.py')
            if os.path.exists(module_file):
                with open(module_file, 'r', encoding='utf-8') as file:
                    module_node = ast.parse(file.read(), filename=module_file)
                module_collector = DefinitionCollector()
                module_collector.visit(module_node)
                module_function_defs = module_collector.function_defs
                function_node = module_function_defs.get(function_name)
                if not function_node:
                    return
            else:
                return

        called_functions = set()
        for n in ast.walk(function_node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name):
                    called_func = n.func.id
                    called_functions.add((None, called_func))
                    visit_function(called_func)
                elif isinstance(n.func, ast.Attribute):
                    if isinstance(n.func.value, ast.Name):
                        base_name = n.func.value.id
                        attr_name = n.func.attr
                        if base_name in import_aliases:
                            module_alias = import_aliases[base_name]
                            called_functions.add((module_alias, attr_name))
                            visit_function(attr_name, module_alias)
                    # Handle other cases as needed
        call_graph[key] = called_functions

    visit_function(target_function)

    return visited_functions, call_graph

def print_dependency_chain(call_graph, target_function):
    from collections import defaultdict

    # Build an adjacency list for the call graph
    adj_list = defaultdict(list)
    for caller, callees in call_graph.items():
        adj_list[caller].extend(callees)

    # Recursive function to print the dependency chain
    def print_chain(function, indent="", visited=None):
        if visited is None:
            visited = set()
        if function in visited:
            print(f"{indent}{function[1]} (recursive call)")
            return
        visited.add(function)
        print(f"{indent}{function[1]}")
        for callee in adj_list.get(function, []):
            print_chain(callee, indent + "    ", visited)

    # Start printing from the target function
    module_name = None
    if '.' in target_function:
        parts = target_function.split('.')
        function_name = parts[-1]
        module_name = '.'.join(parts[:-1])
    else:
        function_name = target_function

    print_chain((module_name, function_name))

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
        if dirs:
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
        call_graph = None  # Initialize call_graph to None

        file_loader = FileLoader(self.root_directory)
        file_paths, file_contents = file_loader.get_python_files()

        if target_module_function:
            try:
                module_path, function_name = target_module_function.rsplit('.', 1)
                file_path = os.path.join(self.root_directory, module_path.replace('.', os.sep) + '.py')
                dependencies, call_graph = find_function_dependencies(file_path, function_name)
                logging.info(f"Dependencies found: {dependencies}")
                filtered_paths = set()
                function_to_file = {}

                # Map functions to their files
                for path, content in zip(file_paths, file_contents):
                    relative_path = os.path.relpath(path, self.root_directory)
                    module_name = os.path.splitext(relative_path.replace(os.path.sep, '.'))[0].lstrip(".")
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            key = (module_name or None, node.name)
                            function_to_file[key] = path

                # Collect files containing the necessary functions
                for module_name, func_name in dependencies:
                    key = (module_name, func_name)
                    if key in function_to_file:
                        filtered_paths.add(function_to_file[key])

                filtered_file_paths = []
                filtered_file_contents = []
                for path, content in zip(file_paths, file_contents):
                    if path in filtered_paths:
                        filtered_file_paths.append(path)
                        filtered_file_contents.append(content)

                file_paths, file_contents = filtered_file_paths, filtered_file_contents
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

        # Write the output, including the dependency chain
        self._write_output(structure_builder.tree, code_aggregator.code, call_graph, target_module_function)
        self._calculate_tokens(code_aggregator.code)

    def _write_output(self, tree, code, call_graph, target_function):
        output_file_path = 'output.txt'
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write("### ===== File Structure ===== ###\n")
            self._write_structure(tree, file)
            if call_graph and target_function:
                file.write("\n### ===== Dependency Chain ===== ###\n")
                dependency_chain_str = self._get_dependency_chain_str(call_graph, target_function)
                file.write(dependency_chain_str)
            file.write("\n### ===== Combined Code ===== ###\n\n")
            file.write(code)
            
    def _get_dependency_chain_str(self, call_graph, target_function):
        from collections import defaultdict

        # Build an adjacency list for the call graph
        adj_list = defaultdict(list)
        for caller, callees in call_graph.items():
            adj_list[caller].extend(callees)

        # Recursive function to build the dependency chain string
        def build_chain(function, indent="", visited=None):
            if visited is None:
                visited = set()
            if function in visited:
                return f"{indent}{function[1]} (recursive call)\n"
            visited.add(function)
            result = f"{indent}{function[1]}\n"
            for callee in adj_list.get(function, []):
                result += build_chain(callee, indent + "    ", visited)
            return result

        # Start building from the target function
        if '.' in target_function:
            parts = target_function.split('.')
            function_name = parts[-1]
            module_name = '.'.join(parts[:-1]) or None
        else:
            function_name = target_function
            module_name = None

        dependency_chain_str = build_chain((module_name, function_name))
        return dependency_chain_str


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
