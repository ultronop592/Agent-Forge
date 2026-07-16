import json
import logging
from typing import List, Dict, Any
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
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def retrieve_memories(self, query: str, category: str = "factual") -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            # 1. Fetch query vector
            query_vector = self.get_embedding(query)
            
            # 2. Fetch all memories for the category
            all_mems = db.query(Memory).filter(Memory.category == category).all()
            
            results = []
            for mem in all_mems:
                score = 0.0
                content_lower = mem.content.lower()
                
                # Check if it contains serialized JSON embedding
                if mem.embedding_searchable_text:
                    try:
                        vector = json.loads(mem.embedding_searchable_text)
                        if isinstance(vector, list) and len(vector) > 0 and isinstance(vector[0], (int, float)):
                            score = self._cosine_similarity(query_vector, vector)
                            if score < 0.60:
                                score = 0.0
                        else:
                            # Not a list, treat as legacy text containment fallback
                            score = 0.0
                    except json.JSONDecodeError:
                        # Fallback keyword match for legacy non-embedding memories
                        score = 0.0
                
                # If no embedding match or embedding parsing failed, use simple keyword containment fallback
                if score == 0.0:
                    words = query.lower().split()
                    word_matches = sum(1 for w in words if w in content_lower)
                    # Normalize word matches to a small score range [0.0 - 0.2] to prioritize semantic vectors
                    if words:
                        score = (word_matches / len(words)) * 0.2
                    else:
                        score = 0.0
                
                # Only keep matches that are reasonably relevant
                if score > 0.05:
                    results.append((score, mem.to_dict()))
            
            # Sort by search score descending
            results.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in results[:5]]
        except Exception as e:
            self.log_db("SYSTEM", None, "error", f"Memory recall error: {str(e)}")
            return []
        finally:
            db.close()

    def store_memory(self, content: str, category: str = "factual") -> Dict[str, Any]:
        db = SessionLocal()
        try:
            # Generate embedding
            embedding = self.get_embedding(content)
            embedding_json = json.dumps(embedding)
            
            mem = Memory(
                category=category,
                content=content,
                embedding_searchable_text=embedding_json
            )
            db.add(mem)
            db.commit()
            db.refresh(mem)
            return mem.to_dict()
        except Exception as e:
            self.log_db("SYSTEM", None, "error", f"Memory storage error: {str(e)}")
            return {}
        finally:
            db.close()

    async def run_subtask(self, subtask_title: str, subtask_desc: str, task_id: str, subtask_id: str) -> str:
        # Search memory for context
        self.log_db(task_id, subtask_id, "thinking", f"Searching memory bank for keywords in: '{subtask_title}'")
        recalled = self.retrieve_memories(subtask_title)
        
        recalled_str = "No relevant long-term memories retrieved."
        if recalled:
            recalled_str = "\n".join([f"- [{m['category']}] {m['content']} (saved at {m['created_at']})" for m in recalled])
            self.log_db(task_id, subtask_id, "output", f"Retrieved {len(recalled)} long-term memories.")
        else:
            self.log_db(task_id, subtask_id, "output", "No matching historical items found in long-term memory.")

        prompt = (
            f"You have been assigned the subtask: {subtask_title}\n"
            f"Subtask Details: {subtask_desc}\n\n"
            f"Here are the recalled memories from previous tasks:\n"
            f"{recalled_str}\n\n"
            "Formulate a synthesis showing how historical context informs the current task."
        )

        mock_memory_report = (
            f"# Historical Context Synthesis: {subtask_title}\n\n"
            "## 1. Past Learnings Review\n"
            f"Search query: \"{subtask_title}\". Recalled data analysis:\n{recalled_str}\n\n"
            "## 2. Context Integration\n"
            "Based on historical records, our system previously successfully designed and validated multi-agent workflows. "
            "Past reviews highlight standard guidelines: ensure all agent functions are modular, avoid hardcoded settings, "
            "and enforce verification layers to check fact consistency. We will follow these patterns in the current cycle."
        )

        output = await self.execute_llm(
            prompt=prompt,
            task_id=task_id,
            subtask_id=subtask_id,
            mock_response_content=mock_memory_report
        )
        return output
