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

    def get_embedding(self, text: str) -> List[float]:
        if not self.has_llm:
            # Fallback mock embedding in case LLM is disabled/offline
            return [0.1] * 768
        try:
            # Request embedding vector using Gemini model
            response = self.client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=text
            )
            if response and response.embeddings:
                return response.embeddings[0].values
            return [0.1] * 768
        except Exception as e:
            logger.error(f"Failed to generate embedding via API: {e}")
            return [0.1] * 768

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        if _HAS_NUMPY:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
                    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
                    if denom == 0.0:
                        return 0.0
                    return float(np.dot(va, vb) / denom)
            except Exception:
                pass


        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)


    def retrieve_memories(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.45,
    ) -> tuple[List[Dict[str, Any]], List[float]]:
        db = SessionLocal()
        try:
            # 1. Fetch query vector using Gemini embedding
            query_vector = self.get_embedding(query)

            # Determine whether database dialect supports native pgvector (<=>)
            is_sqlite = False
            try:
                if db.bind:
                    is_sqlite = (db.bind.dialect.name == "sqlite")
            except Exception:
                is_sqlite = True

            # 2. Native indexed pgvector search on PostgreSQL
            if not is_sqlite and hasattr(Memory, "embedding"):
                try:
                    dist_expr = Memory.embedding.cosine_distance(query_vector)
                    sim_expr = (1.0 - dist_expr).label("similarity_score")

                    q = db.query(Memory, sim_expr).filter(Memory.embedding.isnot(None))
                    if category and category.strip() and category.strip().lower() != "all":
                        q = q.filter(Memory.category == category.strip())

                    # Filter by minimum cosine similarity (distance <= 1 - min_score)
                    q = q.filter(dist_expr <= (1.0 - min_score))
                    q = q.order_by(dist_expr.asc()).limit(top_k)

                    rows = q.all()
                    if rows:
                        results = []
                        for mem, sim in rows:
                            sim_score = max(0.0, float(sim))
                            mem_dict = mem.to_dict()
                            mem_dict["similarity_score"] = round(sim_score, 4)
                            mem_dict["match_percentage"] = f"{int(round(sim_score * 100))}%"
                            results.append(mem_dict)
                        return results, query_vector
                except Exception as pg_err:
                    logger.warning(f"Native pgvector query failed, falling back to Python scan: {pg_err}")

            # 3. Fallback: in-Python scan (SQLite, missing extension, or keyword fallback)
            db_query = db.query(Memory)
            if category and category.strip() and category.strip().lower() != "all":
                db_query = db_query.filter(Memory.category == category)

            all_mems = db_query.all()

            results = []
            for mem in all_mems:
                score = 0.0
                content_lower = mem.content.lower()

                # Vector Cosine Similarity Search: check mem.embedding or JSON string
                if mem.embedding is not None and isinstance(mem.embedding, (list, tuple)) and len(mem.embedding) > 0:
                    score = self._cosine_similarity(query_vector, list(mem.embedding))
                elif mem.embedding_searchable_text:
                    try:
                        vector = json.loads(mem.embedding_searchable_text)
                        if isinstance(vector, list) and len(vector) > 0 and isinstance(vector[0], (int, float)):
                            score = self._cosine_similarity(query_vector, vector)
                    except Exception:
                        score = 0.0

                # Fallback: keyword matching if no vector match
                if score < 0.10:
                    words = query.lower().split()
                    word_matches = sum(1 for w in words if len(w) > 3 and w in content_lower)
                    if words:
                        score = (word_matches / len(words)) * 0.35

                if score >= min_score:
                    mem_dict = mem.to_dict()
                    mem_dict["similarity_score"] = round(score, 4)
                    mem_dict["match_percentage"] = f"{int(round(score * 100))}%"
                    results.append((score, mem_dict))

            # Sort by search score descending
            results.sort(key=lambda x: x[0], reverse=True)
            top_memories = [item[1] for item in results[:top_k]]
            return top_memories, query_vector

        except Exception as e:
            logger.error(f"Memory recall error: {e}")
            self.log_db("SYSTEM", None, "error", f"Memory recall error: {str(e)}")
            return [], [0.1] * 768
        finally:
            db.close()

    def store_memory(
        self,
        content: str,
        category: str = "factual",
        embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            # Re-use pre-computed embedding if available, avoiding an extra API call
            if embedding is not None and len(embedding) > 0:
                embedding_vector = embedding
            else:
                embedding_vector = self.get_embedding(content)

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
            f"# 🧠 Historical Context Synthesis: {subtask_title}\n\n"
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
