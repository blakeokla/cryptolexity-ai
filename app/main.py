from fastapi import FastAPI, HTTPException, BackgroundTasks
from celery import Celery
from redis import Redis
from typing import Optional
import uuid

app = FastAPI()
redis_client = Redis(host='localhost', port=6379, db=0)
celery_app = Celery('tasks', broker='pyamqp://guest@localhost//')

@app.post("/ask")
async def ask_question(question: Question, background_tasks: BackgroundTasks):
    trace_id = str(uuid.uuid4())
    
    # Check cache first
    cached_response = redis_client.get(f"qa:{question.text}")
    if cached_response:
        return {
            "trace_id": trace_id,
            "answer": cached_response,
            "cached": True
        }
    
    # Queue the task
    task = process_question.delay(question.text, trace_id)
    
    return {
        "trace_id": trace_id,
        "status": "processing",
        "task_id": task.id
    }

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    task_result = celery_app.AsyncResult(task_id)
    if task_result.ready():
        return {
            "status": "completed",
            "result": task_result.get()
        }
    return {"status": "processing"} 