# PyBundle: Python Function Dependency Isolator

PyBundle is a Python utility designed to help developers understand and isolate dependencies within their Python projects. By specifying a target module and function, PyBundle analyzes the dependency chain, outputs only the relevant Python files, and provides a clear visualization of their structure.

## Features

- **Dependency Analysis**: Identifies and isolates the function dependency chain within a Python project.
- **Code Aggregation**: Outputs a combined code file containing only the code relevant to the specified function's dependencies.
- **Structure Visualization**: Generates a clear directory structure of the analyzed Python files.

## Requirements

- Python 3.6 or higher
- `argparse` for command-line parsing
- `ast` for analyzing Python abstract syntax trees
- `os` and `fnmatch` for file and directory manipulation
- `tiktoken` (ensure this is the correct module for tokenizing or adjust as necessary)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://your-repository-url/pybundle.git
   cd pybundle
   ```

2. **Setup a virtual environment (optional but recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run PyBundle by specifying the target module and function directly from the command line. Ensure you activate the virtual environment if you've set one up.

```bash
./pybundle.py module.submodule.function_name
```

### Arguments

- **target** (optional): The target module and function in the format `module.submodule.function`. If omitted, PyBundle processes all Python files in the directory.

### Example

```bash
./pybundle.py test.sub-test.function_test
```

This command will analyze the `function_test` function located within the `sub-test` module under the `test` directory, outputting only the files that are relevant to its execution.

## Output

The output consists of two main sections:

- **File Structure**: Displays the directory structure of the analyzed files.
- **Combined Code**: Contains the aggregated Python code relevant to the specified function's dependencies.

The results are saved in an output file named `output.txt` in the root directory.

## Contributing

Contributions are welcome! If you have suggestions for improvements or want to contribute to the development of PyBundle, please follow these steps:

1. **Fork the repository** on GitHub.
2. **Create a new branch**: `git checkout -b your-branch-name`.
3. **Make your changes** and commit them: `git commit -am 'Add some feature'`.
4. **Push to the branch**: `git push origin your-branch-name`.
5. **Submit a pull request** through the GitHub website.

Please ensure your commits are neatly packaged and that your code is well-documented.

## License

This project is open source and available under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html).
