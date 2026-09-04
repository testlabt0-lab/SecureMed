import os
import json
import tokenize
from io import BytesIO

def process_file(filepath, mapping, counter):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    tokens = list(tokenize.tokenize(BytesIO(content).readline))
    
    out_tokens = []
    modified = False
    
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            comment_text = tok.string
            # Keep encoding declarations on the first two lines
            if tok.start[0] <= 2 and 'coding:' in comment_text:
                out_tokens.append((tok.type, tok.string))
                continue
            
            counter[0] += 1
            ref_id = f"Comment_{counter[0]}"
            mapping[ref_id] = comment_text
            
            # replace the comment
            new_comment = f"# {ref_id}"
            out_tokens.append((tokenize.COMMENT, new_comment))
            modified = True
        else:
            out_tokens.append((tok.type, tok.string))
            
    if modified:
        try:
            # Reconstruct the code
            new_code = tokenize.untokenize(out_tokens).decode('utf-8')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_code)
        except Exception as e:
            print(f"Failed to untokenize {filepath}: {e}")

def main():
    backend_dir = r"c:\Users\Essa\Downloads\securemed\backend"
    mapping = {}
    counter = [0]
    
    for root, dirs, files in os.walk(backend_dir):
        # skip virtual environments, migrations, tests, and caches
        dirs[:] = [d for d in dirs if d not in (
            'venv', '.venv', 'migrations', 'tests', '__pycache__', '.pytest_cache', 'htmlcov'
        )]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    process_file(filepath, mapping, counter)
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
                    
    mapping_path = r"c:\Users\Essa\Downloads\securemed\comments_mapping.json"
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=4)
    print(f"Successfully extracted {counter[0]} comments to {mapping_path}")
        
if __name__ == "__main__":
    main()
