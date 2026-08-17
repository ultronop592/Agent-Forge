from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from backend.app.database.connection import Base

def generate_uuid():
    return str(uuid.uuid4())

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    prompt = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, awaiting_plan_approval, running, awaiting_steering, completed, failed, cancelled
    plugin_name = Column(String, nullable=False)
    final_result = Column(Text, nullable=True)
    total_tokens = Column(Integer, nullable=True, default=0)
    total_cost_usd = Column(Float, nullable=True, default=0.0)
    total_latency_ms = Column(Float, nullable=True, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subtasks = relationship("Subtask", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("AgentLog", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self):
        scores = [s.confidence_score for s in self.subtasks if s.confidence_score and s.confidence_score > 0] if self.subtasks else []
        conf = max(scores) if scores else (0.95 if self.status == "completed" else 0.0)
        
        # Aggregate logs telemetry if not explicitly stored
        log_tokens = sum(l.total_tokens or 0 for l in self.logs) if self.logs else 0
        log_cost = sum(l.cost_usd or 0.0 for l in self.logs) if self.logs else 0.0
        log_latency = sum(l.latency_ms or 0.0 for l in self.logs) if self.logs else 0.0

        return {
            "id": self.id,
            "prompt": self.prompt,
            "status": self.status,
            "plugin_name": self.plugin_name,
            "final_result": self.final_result,
            "confidence_score": conf,
            "total_tokens": self.total_tokens or log_tokens,
            "total_cost_usd": round(self.total_cost_usd or log_cost, 6),
            "total_latency_ms": round(self.total_latency_ms or log_latency, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Subtask(Base):
    __tablename__ = "subtasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    assigned_agent = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed
    output = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="subtasks")
    logs = relationship("AgentLog", back_populates="subtask", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "assigned_agent": self.assigned_agent,
            "status": self.status,
            "output": self.output,
            "confidence_score": self.confidence_score,
            "order_index": self.order_index,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    subtask_id = Column(String, ForeignKey("subtasks.id", ondelete="CASCADE"), nullable=True)
    agent_name = Column(String, nullable=False)
    log_type = Column(String, nullable=False)  # thinking, tool_call, output, error, telemetry, manager_decision, steering
    content = Column(Text, nullable=False)
    prompt_tokens = Column(Integer, nullable=True, default=0)
    completion_tokens = Column(Integer, nullable=True, default=0)
    total_tokens = Column(Integer, nullable=True, default=0)
    latency_ms = Column(Float, nullable=True, default=0.0)
    cost_usd = Column(Float, nullable=True, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="logs")
    subtask = relationship("Subtask", back_populates="logs")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "subtask_id": self.subtask_id,
            "agent_name": self.agent_name,
            "log_type": self.log_type,
            "content": self.content,
            "prompt_tokens": self.prompt_tokens or 0,
            "completion_tokens": self.completion_tokens or 0,
            "total_tokens": self.total_tokens or 0,
            "latency_ms": round(self.latency_ms or 0.0, 2),
            "cost_usd": round(self.cost_usd or 0.0, 6),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Memory(Base):
    __tablename__ = "memories"

    id = Column(String, primary_key=True, default=generate_uuid)
    category = Column(String, default="factual")  # factual, semantic, execution_log
    content = Column(Text, nullable=False)
    embedding_searchable_text = Column(Text, nullable=True)  # Simple keywords/text for queries
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "content": self.content,
            "embedding_searchable_text": self.embedding_searchable_text,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True)
    transport = Column(String, default="stdio")  # stdio, sse
    command = Column(String, nullable=True)  # e.g. "npx" or "python"
    args = Column(String, nullable=True)  # JSON-string array of arguments
    url = Column(String, nullable=True)  # For SSE transport
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "transport": self.transport,
            "command": self.command,
            "args": self.args,
            "url": self.url,
            "is_active": self.is_active
        }
