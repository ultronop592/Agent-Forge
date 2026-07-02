import asyncio
import os
import sys

# Ensure backend directory is in python load path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database.connection import engine, Base, SessionLocal
from backend.app.database.models import Task, Subtask, AgentLog
from backend.app.workflows.orchestrator import orchestrator_graph
from backend.app.workflows.state import AgentState

async def run_test():
    print("=== AgentForge Integration Verification ===")
    
    # 1. Initialize DB and create tables
    print("\n1. Initializing SQLite tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Database tables created successfully.")
    except Exception as e:
        print(f"[FAIL] Failed to create tables: {e}")
        return False

    db = SessionLocal()
    
    # 2. Seed a test task
    print("\n2. Seeding test Task...")
    try:
        task = Task(
            prompt="Analyze the growth pattern of decentralized open-source LLM plugins.",
            plugin_name="startup_research",
            status="pending"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        print(f"[OK] Created Task in DB with ID: {task.id}")
    except Exception as e:
        print(f"[FAIL] Seeding failed: {e}")
        db.close()
        return False

    # 3. Compile and Run LangGraph Flow
    print("\n3. Launching LangGraph orchestrator graph...")
    try:
        initial_state: AgentState = {
            "task_id": task.id,
            "prompt": task.prompt,
            "plugin_name": task.plugin_name,
            "subtasks": [],
            "current_subtask_index": 0,
            "agent_outputs": {},
            "verification_results": {},
            "final_result": ""
        }
        
        await orchestrator_graph.ainvoke(initial_state)
        print("[OK] LangGraph flow compiled and ran successfully.")
    except Exception as e:
        print(f"[FAIL] Graph execution failed: {e}")
        db.close()
        return False

    # 4. Verify Task state and logs in Database
    print("\n4. Verifying DB state outputs...")
    try:
        db.refresh(task)
        print(f"  Task Status: {task.status}")
        
        subtasks = db.query(Subtask).filter(Subtask.task_id == task.id).all()
        print(f"  Subtasks generated: {len(subtasks)}")
        for sub in subtasks:
            print(f"    - [{sub.assigned_agent}] {sub.title} -> {sub.status}")
            
        logs = db.query(AgentLog).filter(AgentLog.task_id == task.id).all()
        print(f"  Agent logs recorded: {len(logs)}")
        
        if len(subtasks) > 0 and len(logs) > 0 and task.status == "completed":
            print("\n[OK] Integration test completed with 100% SUCCESS.")
            db.close()
            return True
        else:
            print("\n[FAIL] Verification failed. Incomplete database state records.")
            db.close()
            return False
            
    except Exception as e:
        print(f"[FAIL] Verification checks failed: {e}")
        db.close()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_test())
    if not success:
        sys.exit(1)
