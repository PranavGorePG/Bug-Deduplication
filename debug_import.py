try:
    import pydantic_settings
    print("pydantic_settings imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
