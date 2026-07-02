from typing import List, Dict, Any
from backend.app.agents.base import BaseAgent
from backend.app.database.connection import SessionLocal
from backend.app.database.models import Memory

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

    def retrieve_memories(self, query: str, category: str = "factual") -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            # Basic keyword containment search for SQLite database
            words = query.lower().split()
            all_mems = db.query(Memory).filter(Memory.category == category).all()
            
            results = []
            for mem in all_mems:
                score = 0
                content_lower = mem.content.lower()
                for word in words:
                    if word in content_lower:
                        score += 1
                if score > 0 or not words:
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
            mem = Memory(
                category=category,
                content=content,
                embedding_searchable_text=content[:200]
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
