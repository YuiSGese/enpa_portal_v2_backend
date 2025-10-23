import os
import sys

LAYERS = {
    "api/controllers": "controller",
    "api/routes": "router",
    "api/validators": "validator",
    "domain/entities": "entity",
    "domain/repositories": "repository",
    "domain/services": "service",
}

def create_tool(tool_name):
    base_dir = "app"
    for path, suffix in LAYERS.items():
        dir_path = os.path.join(base_dir, path)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, f"{tool_name}_{suffix}.py")
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                f.write(f"# {tool_name}_{suffix}.py\n")
            print(f"✅ Created: {file_path}")
        else:
            print(f"⚠️ Already exists: {file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/new_tool.py tool_name")
        sys.exit(1)
    tool_name = sys.argv[1]
    create_tool(tool_name)