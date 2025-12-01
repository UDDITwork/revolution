"""
Script to delete and recreate Pinecone index with correct dimensions (2048)
Run this once to fix the dimension mismatch issue.
"""
import os
from pinecone import Pinecone, ServerlessSpec

# Set your API key
pinecone_api_key = "pcsk_6gnLLw_A6q2fArU3PN79CKpsdc7EoS3DLtVUxjsNVk5SxinPwjdHwGWXcxVMQyEZBRSQ1n"

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)

index_name = "multimodal-rag"

print(f"Checking for existing index: {index_name}")

# Delete existing index if it exists
existing_indexes = pc.list_indexes().names()
if index_name in existing_indexes:
    print(f"Deleting existing index: {index_name}")
    pc.delete_index(index_name)
    print("Index deleted successfully")
else:
    print("No existing index found")

# Create new index with 2048 dimensions
print(f"\nCreating new index with 2048 dimensions...")
pc.create_index(
    name=index_name,
    dimension=2048,  # llama-3.2-nv-embedqa-1b-v2 default dimension
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    )
)

print(f"Successfully created new Pinecone index: {index_name}")
print(f"   - Dimension: 2048")
print(f"   - Metric: cosine")
print(f"   - Cloud: AWS (us-east-1)")
print("\nYou can now run your Streamlit app!")
