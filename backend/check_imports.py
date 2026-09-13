import traceback, sys
print(f"Python: {sys.version}")

modules = [
    "fastapi", "uvicorn", "sqlmodel", "reportlab", "sklearn",
    "shap", "sentence_transformers", "faiss", "groq",
    "jwt", "passlib", "bcrypt", "multipart", "dotenv",
    "numpy", "pandas"
]

for mod in modules:
    try:
        __import__(mod)
        print(f"  [OK] {mod}")
    except Exception as e:
        print(f"  [FAIL] {mod}: {e}")

print("\n--- Importing main ---")
try:
    import main
    print("[OK] main imported successfully")
except Exception as e:
    traceback.print_exc()
