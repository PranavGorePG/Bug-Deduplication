import sys
import os

# Add root directory to path so we can import app
sys.path.append(os.getcwd())

from app.services.vector_store_service import VectorStoreService

def debug_store():
    service = VectorStoreService()
    print("Vector Store Loaded")
    
    if service.vector_store and service.vector_store.docstore._dict:
        print(f"Total documents: {len(service.vector_store.docstore._dict)}")
        
        # Check first 3 documents
        count = 0
        for doc_id, doc in service.vector_store.docstore._dict.items():
            print(f"\n--- Doc ID: {doc_id} ---")
            keys = list(doc.metadata.keys())
            print(f"Metadata keys: {keys}")
            
            repro = doc.metadata.get('repro_steps', 'NOT FOUND')
            if repro == 'NOT FOUND':
                print("Repro Steps: NOT FOUND")
            elif not repro:
                print("Repro Steps: EMPTY STRING")
            else:
                print(f"Repro Steps: PRESENT (Length: {len(repro)})")
                print(f"Snippet: {repro[:50]}...")
            
            count += 1
            if count >= 3:
                break
    else:
        print("Vector store is empty or not loaded correctly.")

if __name__ == "__main__":
    debug_store()
