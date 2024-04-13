#!.venv/bin/python
import os
import tiktoken


encoding = tiktoken.encoding_for_model("gpt-4")

# Get all Python file paths in the current directory
file_paths = [f for f in os.listdir('.') if f.endswith('.py')]

# Initialize an empty string to store the combined code
combined_code = ""

# Loop through each file path
for file_path in file_paths:
    # Open the file in read mode
    with open(file_path, 'r') as file:
        # Read the entire file content
        file_content = file.read()

        # Add a separator with the module name
        module_name = os.path.splitext(file_path)[0]  # Get file name without extension
        if module_name == 'pybundle':
            continue
        combined_code += f"Module: {module_name}.py\n\n" 
        combined_code += file_content + "\n\n###\n"

# Write the combined code to an output file
output_file_path = 'concat.txt'
with open(output_file_path, 'w') as output_file:
    output_file.write(combined_code)

num_tokens = len(encoding.encode(combined_code))
print(f"Number of tokens: {num_tokens}")