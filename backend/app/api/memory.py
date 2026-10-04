from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
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
            category=category if category and category.lower() != "all" else None,
            top_k=50,
            min_score=0.15
        )
        if recalled_memories:
            return recalled_memories

        # Keyword fallback if vector similarity returned no high-confidence hits
        q = db.query(Memory)
        if category and category.strip() and category.lower() != "all":
            q = q.filter(Memory.category == category)
        keyword_filter = f"%{query.strip().lower()}%"
        fallback_mems = q.filter(Memory.content.ilike(keyword_filter)).order_by(Memory.created_at.desc()).limit(50).all()
        return [m.to_dict() for m in fallback_mems]

    # Otherwise, return all memories sorted by newest first
    q = db.query(Memory)
    if category and category.strip() and category.lower() != "all":
        q = q.filter(Memory.category == category)
    
    memories = q.order_by(Memory.created_at.desc()).all()
    return [m.to_dict() for m in memories]

@router.get("/stats")
def get_memory_stats(db: Session = Depends(get_db)):
    """Return counts by category and total knowledge records."""
    total = db.query(Memory).count()
    factual = db.query(Memory).filter(Memory.category == "factual").count()
    insight = db.query(Memory).filter(Memory.category == "insight").count()
    code = db.query(Memory).filter(Memory.category == "code").count()
    other = max(0, total - (factual + insight + code))
    return {
        "total": total,
        "categories": {
            "all": total,
            "factual": factual,
            "insight": insight,
            "code": code,
            "other": other
        }
    }

@router.post("")
def add_memory(payload: MemoryCreate, db: Session = Depends(get_db)):
    return memory_agent.store_memory(
        content=payload.content,
        category=payload.category
    )

@router.delete("/{memory_id}")
def delete_memory(memory_id: str, db: Session = Depends(get_db)):
    """Delete an individual memory record by ID."""
    success = memory_agent.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Memory node '{memory_id}' not found")
    return {"message": "Memory deleted successfully", "id": memory_id}

@router.delete("")
def clear_memories(category: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    """Bulk delete memories, optionally filtered by category."""
    deleted_count = memory_agent.clear_memories(category=category)
    return {"message": f"Successfully deleted {deleted_count} memory records", "count": deleted_count}
