from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from backend.app.database.connection import get_db
from backend.app.database.models import Memory
from backend.app.agents.memory_agent import MemoryAgent

router = APIRouter(prefix="/memory", tags=["memory"])

memory_agent = MemoryAgent()

class MemoryCreate(BaseModel):
    category: str = "factual"
    content: str

@router.get("")
def query_memory(
    query: str = Query(default=""),
    category: str = Query(default=""),
    db: Session = Depends(get_db)
):
    # If query is provided, perform Cosine Similarity Vector Search!
    if query and query.strip():
        recalled_memories, _ = memory_agent.retrieve_memories(
            query=query.strip(),
            category=category if category else None,
            top_k=20,
            min_score=0.20
        )
        return recalled_memories

    # Otherwise, return all memories sorted by newest first
    q = db.query(Memory)
    if category and category.strip() and category.lower() != "all":
        q = q.filter(Memory.category == category)
    
    memories = q.order_by(Memory.created_at.desc()).all()
    return [m.to_dict() for m in memories]

@router.post("")
def add_memory(payload: MemoryCreate, db: Session = Depends(get_db)):
    return memory_agent.store_memory(
        content=payload.content,
        category=payload.category
    )
