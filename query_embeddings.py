import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from tqdm import tqdm

def load_vectorstore():
    """Load the saved vector store"""
    print("Loading vector store...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-ada-002",
        show_progress_bar=True
    )
    vectorstore = FAISS.load_local(
        "protocol_embeddings", 
        embeddings,
        allow_dangerous_deserialization=True
    )
    print("Vector store loaded successfully!")
    return vectorstore

def create_chain():
    """Create a conversation chain"""
    vectorstore = load_vectorstore()
    
    print("Initializing ChatGPT...")
    llm = ChatOpenAI(
        model_name="gpt-4o-mini",
        temperature=0
    )
    
    print("Creating conversation chain...")
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(
            search_kwargs={"k": 100}
        ),
        return_source_documents=True,
        verbose=True
    )
    
    return chain

def main():
    print("Initializing RAG system...")
    # Create the chain
    chain = create_chain()
    chat_history = []
    
    print("\nReady to answer questions! (Type 'quit' to exit)")
    print("-" * 50)
    
    # Start conversation loop
    while True:
        question = input("\nEnter your question (or 'quit' to exit): ")
        
        if question.lower() == 'quit':
            break
        
        print("\nProcessing question...")
        result = chain({"question": question, "chat_history": chat_history})
        
        print("\nAnswer:", result["answer"])
        
        chat_history.append((question, result["answer"]))

if __name__ == "__main__":
    main() 