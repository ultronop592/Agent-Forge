import json
import logging
from typing import List, Dict, Any, Optional

_HAS_NUMPY = False
try:
    import sys
    if sys.version_info < (3, 14):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import numpy as np
            _dummy = np.dot(np.array([1.0], dtype=np.float32), np.array([1.0], dtype=np.float32))
            _HAS_NUMPY = True
except Exception:
    _HAS_NUMPY = False


from backend.app.agents.base import BaseAgent
from backend.app.database.connection import SessionLocal
from backend.app.database.models import Memory
from backend.app.database.memory_search import search_similar, _cosine_similarity

logger = logging.getLogger("agentforge.agents.memory")


class MemoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="MemoryAgent",
            system_instruction=(
                "You are the Lead Memory Agent. Your role is to store knowledge, query long-term "
                "task history, and retrieve context for the current run. You summarize key learnings "
                "to keep the organization's memory sharp."
            )
        )

    def _normalize_vector(self, v: List[float]) -> List[float]:
        norm = sum(x * x for x in v) ** 0.5
        if norm == 0.0:
            return v
        return [x / norm for x in v]

    def get_embedding(self, text: str) -> List[float]:
        if not self.has_llm:
            return self._normalize_vector([0.1] * 768)
        try:
            response = self.client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=text,
                config={"output_dimensionality": 768}
            )
            if response and response.embeddings:
                return self._normalize_vector(response.embeddings[0].values)
            return self._normalize_vector([0.1] * 768)
        except Exception as e:
            logger.error(f"Failed to generate embedding via API: {e}")
            return self._normalize_vector([0.1] * 768)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        return _cosine_similarity(a, b)

    def retrieve_memories(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.45,
        user_id: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], List[float]]:
        db = SessionLocal()
        try:
            query_vector = self._normalize_vector(self.get_embedding(query))
            results = search_similar(
                session=db,
                query_embedding=query_vector,
                k=top_k,
                min_similarity=min_score,
                category=category,
                user_id=user_id,
                query_text=query
            )
            return results, query_vector
        except Exception as e:
            logger.error(f"Memory recall error: {e}")
            self.log_db("SYSTEM", None, "error", f"Memory recall error: {str(e)}")
            return [], self._normalize_vector([0.1] * 768)
        finally:
            db.close()

    def store_memory(
        self,
        content: str,
        category: str = "factual",
        embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        if embedding is not None and len(embedding) != 768:
            raise ValueError(f"Expected 768-dim embedding, got {len(embedding)}")

        db = SessionLocal()
        try:
            if embedding is not None:
                embedding_vector = self._normalize_vector(embedding)
            else:
                embedding_vector = self.get_embedding(content)

            if len(embedding_vector) != 768:
                raise ValueError(f"Expected 768-dim embedding, got {len(embedding_vector)}")

            embedding_json = json.dumps(embedding_vector)

            mem = Memory(
                category=category,
                content=content,
                embedding_searchable_text=embedding_json,
                embedding=embedding_vector,
            )
            db.add(mem)
            db.commit()
            db.refresh(mem)
            logger.info(f"[MemoryAgent] Stored new {category} memory: '{content[:60]}...'")
            return mem.to_dict()
        except Exception as e:
            logger.error(f"Memory storage error: {e}")
            self.log_db("SYSTEM", None, "error", f"Memory storage error: {str(e)}")
            return {}
        finally:
            db.close()

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory node by ID."""
        db = SessionLocal()
        try:
            mem = db.query(Memory).filter(Memory.id == memory_id).first()
            if not mem:
                return False
            db.delete(mem)
            db.commit()
            logger.info(f"[MemoryAgent] Deleted memory node: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def clear_memories(self, category: Optional[str] = None) -> int:
        """Clear memories, optionally filtered by category. Returns count deleted."""
        db = SessionLocal()
        try:
            q = db.query(Memory)
            if category and category.strip() and category.lower() != "all":
                q = q.filter(Memory.category == category.strip())
            count = q.delete(synchronize_session=False)
            db.commit()
            logger.info(f"[MemoryAgent] Cleared {count} memory nodes (category: {category or 'all'})")
            return count
        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")
            db.rollback()
            return 0
        finally:
            db.close()


    async def run_subtask(
        self,
        subtask_title: str,
        subtask_desc: str,
        task_id: str,
        subtask_id: str,
    ) -> tuple[str, List[float]]:
        # Extract meaningful search query from subtask_desc or title
        search_query = subtask_desc if len(subtask_desc) > 10 else subtask_title
        # Clean up prompt prefix if present
        if "related to:" in search_query:
            search_query = search_query.split("related to:")[-1].strip()

        self.log_db(
            task_id,
            subtask_id,
            "thinking",
            f"Performing Cosine Similarity Vector Search over Memory Bank for: '{search_query[:80]}...'"
        )

        # Retrieve top 5 semantic vector matches across all categories
        recalled, query_vector = self.retrieve_memories(search_query, category=None, top_k=5, min_score=0.45)

        recalled_str = "No relevant long-term memories retrieved."
        if recalled:
            match_bullets = [
                f"- [{m['category'].upper()} | Match: {m.get('match_percentage', 'N/A')}] {m['content']} (saved {m['created_at'][:10]})"
                for m in recalled
            ]
            recalled_str = "\n".join(match_bullets)
            scores_str = ", ".join([m.get('match_percentage', '') for m in recalled])

            self.log_db(
                task_id,
                subtask_id,
                "output",
                f"🧠 Recalled {len(recalled)} historical memory entry(s) [Matches: {scores_str}].\n\n{recalled_str}"
            )
        else:
            self.log_db(
                task_id,
                subtask_id,
                "output",
                "No matching historical items found in long-term memory above 45% similarity threshold."
            )

        prompt = (
            f"You have been assigned the subtask: {subtask_title}\n"
            f"Subtask Details: {subtask_desc}\n\n"
            f"Recalled Vector Memories from Previous Workforce Tasks:\n"
            f"{recalled_str}\n\n"
            "Formulate a synthesis showing how historical context and past task learnings inform the current task."
        )

        mock_memory_report = (
            f"#  Historical Context Synthesis: {subtask_title}\n\n"
            "## 1. Vector Search Audit\n"
            f"**Search Target:** `{search_query[:100]}`  \n"
            f"**Recalled Insights:**\n{recalled_str}\n\n"
            "## 2. Context Integration & Architectural Guidelines\n"
            "Based on historical records, our system previously successfully executed similar workflows. "
            "Past reviews highlight key patterns: ensure all agent functions are modular, enforce self-healing "
            "verification loops, and maintain type safety. We will incorporate these learnings into the current run."
        )

        output = await self.execute_llm(
            prompt=prompt,
            task_id=task_id,
            subtask_id=subtask_id,
            mock_response_content=mock_memory_report
        )
        return output, query_vector
