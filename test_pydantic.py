#!/usr/bin/env python3
"""
Quick test to verify Pydantic import works
"""

try:
    import pydantic
    print(f"✅ Pydantic {pydantic.__version__} imported successfully!")
    
    from pydantic import BaseModel
    
    class TestModel(BaseModel):
        name: str
        value: int
    
    test = TestModel(name="test", value=42)
    print(f"✅ Pydantic model works: {test}")
    
except ImportError as e:
    print(f"❌ Pydantic import failed: {e}")
except Exception as e:
    print(f"❌ Pydantic test failed: {e}")
