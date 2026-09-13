from pathlib import Path

root = Path(".")

folders = [
    "src/api",
    "src/core",
    "src/rag",
    "src/services",
    "data",
    "templates",
    "static",
    "uploads",
    "tests"
]

files = [
    "src/main.py",
    "ingest_kb.py",
    "run.py"
]


for folder in folders:
    (root / folder).mkdir(parents=True,exist_ok=True)

for file in files:
    (root / file).touch(exist_ok=True)

print("Project Structure Created Successfully")