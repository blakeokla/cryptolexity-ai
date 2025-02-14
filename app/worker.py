from celery import Celery
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import redis

celery_app = Celery('tasks', broker='pyamqp://guest@localhost//')
redis_client = redis.Redis(host='localhost', port=6379, db=0)

class VectorStoreManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = FAISS.load_local(
                "protocol_embeddings",
                OpenAIEmbeddings(model="text-embedding-ada-002"),
                allow_dangerous_deserialization=True
            )
        return cls._instance

@celery_app.task
def process_question(question: str, trace_id: str):
    try:
        vectorstore = VectorStoreManager.get_instance()
        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        
        # Process question
        result = chain.run(question)
        
        # Cache the result
        redis_client.setex(
            f"qa:{question}",
            3600,  # 1 hour cache
            result['answer']
        )
        
        return {
            "trace_id": trace_id,
            "answer": result['answer']
        }
    except Exception as e:
        return {
            "trace_id": trace_id,
            "error": str(e)
        } 