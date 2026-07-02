from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from backend.app.database.connection import get_db
from backend.app.database.models import Memory

router = APIRouter(prefix="/memory", tags=["memory"])

class MemoryCreate(BaseModel):
    category: str = "factual"
    content: str

@router.get("")
def query_memory(
    query: str = Query(default=""),
    category: str = Query(default=""),
    db: Session = Depends(get_db)
):
    q = db.query(Memory)
    if category:
        q = q.filter(Memory.category == category)
    
    memories = q.order_by(Memory.created_at.desc()).all()
    
    if not query:
        return [m.to_dict() for m in memories]
        
    # Standard keyword match logic
    words = query.lower().split()
    results = []
    for m in memories:
        score = 0
        content_lower = m.content.lower()
        for w in words:
            if w in content_lower:
                score += 1
        if score > 0:
            results.append((score, m.to_dict()))
            
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results]

@router.post("")
def add_memory(payload: MemoryCreate, db: Session = Depends(get_db)):
    mem = Memory(
        category=payload.category,
        content=payload.content,
        embedding_searchable_text=payload.content[:200]
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)
    return mem.to_dict()
