import os
import uuid
import logging
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from functools import partial
from langchain.prompts import ChatPromptTemplate

# Configure max workers for concurrent processing
MAX_WORKERS = 10  # Adjust based on your server capacity
thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Configure logging
logging.basicConfig(
    filename='rag_queries.log',
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class Question(BaseModel):
    text: str
    sources: bool = False

class QAChainPool:
    def __init__(self, pool_size=5):  # Create multiple chain instances
        self.chains = []
        for _ in range(pool_size):
            self.chains.append(self._create_chain())
        self.current = 0
    
    def _create_chain(self):
        print(f"Initializing chain {len(self.chains) + 1}...")
        embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            show_progress_bar=True
        )
        vectorstore = FAISS.load_local(
            "protocol_embeddings", 
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Add system message to LLM
        llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0
        )
        
        # Configure retriever to return scores
        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": 25,
                "fetch_k": 50
            },
            search_type="similarity"
        )
        
        # Create prompt template with system message
        template = """System: You are an AI which gives people information about Crypto, Web3 and DeFi. 
        You first try to get the relevant information from the sources, which are trained from our embeddings. 
        If you don't get anything relevant from the sources, use your own knowledge to provide a response.
        You should structure the response in a clear and user-friendly way.

        Important: Only use the provided sources if they are directly relevant to the question. 
        If the sources don't provide meaningful information for this specific query, rely on your own knowledge instead.

        Human: {question}

        Assistant: Let me analyze the available information and provide you with the most accurate response.

        Context from sources:
        {context}

        Based on this information and my knowledge, I will provide a comprehensive answer.
        """
        
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            return_source_documents=True,
            verbose=True,
            chain_type="stuff",
            combine_docs_chain_kwargs={
                "prompt": ChatPromptTemplate.from_messages([
                    ("system", """You are an AI expert in Crypto, Web3 and DeFi. 
                    Analyze the provided context carefully. Only reference sources if they contain relevant information.
                    If the sources aren't helpful for the specific question, use your own knowledge instead.
                    Mark the response with [FROM_SOURCES] at the start if you used the provided sources significantly,
                    otherwise start with [FROM_KNOWLEDGE] to indicate you're using your general knowledge."""),
                    ("human", "{question}"),
                    ("human", "Context from our sources:\n\n{context}"),
                    ("assistant", "I'll provide a detailed response based on the most relevant information available.")
                ])
            }
        )
        return chain
    
    def get_chain(self):
        # Round-robin chain selection
        chain = self.chains[self.current]
        self.current = (self.current + 1) % len(self.chains)
        return chain

# Initialize the chain pool globally
chain_pool = QAChainPool(pool_size=5)  # Create 5 chain instances

def process_question(question: str, chain) -> dict:
    # Remove async since this runs in a thread pool
    return chain({
        "question": question,
        "chat_history": []
    })

@app.post("/ask")
async def ask_question(question: Question):
    # Generate trace ID
    trace_id = str(uuid.uuid4())
    
    try:
        # Log the incoming question
        logging.info(f"TRACE_ID: {trace_id} | QUESTION: {question.text}")
        
        # Get a chain from the pool
        chain = chain_pool.get_chain()
        
        # Process question with timeout using thread pool
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    thread_pool,
                    partial(process_question, question.text, chain)
                ),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            logging.error(f"TRACE_ID: {trace_id} | ERROR: Request timed out after 25 seconds")
            raise HTTPException(status_code=504, detail="Request timed out")
        
        # Log the response
        logging.info(f"TRACE_ID: {trace_id} | ANSWER: {result['answer']}")
        
        # Prepare response based on sources flag
        response = {
            "trace_id": trace_id,
            "answer": result['answer']
        }
        
        if question.sources and result['answer'].startswith('[FROM_SOURCES]'):
            # Only include sources if they were actually used
            protocol_sources = []
            for doc in result["source_documents"]:
                if "NAME:" in doc.page_content:
                    protocol_name = doc.page_content.split("NAME:")[1].split("\n")[0].strip()
                    protocol_url_name = protocol_name.lower().replace(' ', '-')
                    score = float(doc.metadata.get('distance', 0))
                    similarity = 1 / (1 + score)
                    
                    protocol_sources.append({
                        "url": f"https://defillama.com/protocol/{protocol_url_name}",
                        "relevance_score": round(similarity, 3)
                    })
            
            if protocol_sources:  # Only add sources if we found relevant ones
                response["sources"] = sorted(
                    protocol_sources,
                    key=lambda x: x["relevance_score"],
                    reverse=True
                )
        
        # Clean up the response text by removing the source indicator
        response["answer"] = response["answer"].replace('[FROM_SOURCES]', '').replace('[FROM_KNOWLEDGE]', '').strip()
        
        return response
    
    except Exception as e:
        # Log the error
        logging.error(f"TRACE_ID: {trace_id} | ERROR: {str(e)}")
        if isinstance(e, asyncio.TimeoutError):
            raise HTTPException(status_code=504, detail="Request timed out")
        raise HTTPException(status_code=500, detail=str(e))

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    thread_pool.shutdown(wait=True) 