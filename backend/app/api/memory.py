from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from backend.app.database.connection import get_db
from backend.app.database.models import Memory
from backend.app.database.memory_search import search_similar
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
    user_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    # If query is provided, perform Cosine Similarity Vector Search!
    if query and query.strip():
        query_vec = memory_agent._normalize_vector(memory_agent.get_embedding(query.strip()))
        cat_filter = category.strip() if category and category.strip().lower() != "all" else None
        recalled_memories = search_similar(
            session=db,
            query_embedding=query_vec,
            k=50,
            min_similarity=0.15,
            category=cat_filter,
            user_id=user_id,
            query_text=query.strip()
        )
        if recalled_memories:
            return recalled_memories

        # Keyword fallback if vector similarity returned no high-confidence hits
        q = db.query(Memory)
        if cat_filter:
            q = q.filter(Memory.category == cat_filter)
        if user_id is not None and hasattr(Memory, "user_id"):
            q = q.filter(getattr(Memory, "user_id") == user_id)
        keyword_filter = f"%{query.strip().lower()}%"
        fallback_mems = q.filter(Memory.content.ilike(keyword_filter)).order_by(Memory.created_at.desc()).limit(50).all()
        return [m.to_dict() for m in fallback_mems]

    # Otherwise, return all memories sorted by newest first
    q = db.query(Memory)
    if category and category.strip() and category.lower() != "all":
        q = q.filter(Memory.category == category.strip())
    if user_id is not None and hasattr(Memory, "user_id"):
        q = q.filter(getattr(Memory, "user_id") == user_id)
    
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
