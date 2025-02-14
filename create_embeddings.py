import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from tqdm import tqdm
from langchain.schema import Document

def load_documents():
    """Load documents from protocols_for_rag.txt"""
    print("Loading documents...")
    with open('protocols_for_rag.txt', 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Split documents by the separator we used
    raw_documents = content.split('\n\n---\n\n')
    
    # Convert to Document objects
    documents = [
        Document(
            page_content=doc,
            metadata={'doc_id': i}
        ) for i, doc in enumerate(raw_documents)
    ]
    
    print(f"Loaded {len(documents)} documents")
    return documents

def create_embeddings():
    # Load documents
    documents = load_documents()
    
    # Initialize OpenAI embeddings
    print("\nInitializing OpenAI embeddings...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-ada-002",
        show_progress_bar=True
    )
    
    # Create vector store with progress bar
    print("\nCreating vector store (this may take a while)...")
    vectorstore = FAISS.from_documents(
        documents=tqdm(documents, desc="Creating embeddings"),
        embedding=embeddings
    )
    
    # Save vector store locally
    print("\nSaving vector store...")
    vectorstore.save_local("protocol_embeddings")
    
    print("\nEmbeddings created and saved successfully!")
    print(f"Total documents processed: {len(documents)}")

if __name__ == "__main__":
    create_embeddings() 