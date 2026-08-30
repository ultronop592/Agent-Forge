"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BrainCircuit, Search, Calendar, Folder, Plus, Check, Sparkles } from "lucide-react";

interface Memory {
  id: string;
  category: string;
  content: string;
  created_at: string;
  match_percentage?: string;
  similarity_score?: number;
}

export default function MemoryBank() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  
  // Custom memory insertion form
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("factual");
  const [isInserting, setIsInserting] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const loadMemories = async () => {
    try {
      const data = await api.getMemory(searchQuery, selectedCategory);
      setMemories(data);
    } catch (e) {
      console.error("Failed to fetch memories:", e);
    }
  };

  useEffect(() => {
    loadMemories();
  }, [searchQuery, selectedCategory]);

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    
    setIsInserting(true);
    try {
      await api.addMemory(newContent, newCategory);
      setNewContent("");
      setShowForm(false);
      loadMemories();
    } catch (err) {
      console.error("Failed to add memory:", err);
    } finally {
      setIsInserting(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 w-full relative z-10 bg-[#121214] text-[#f4f4f5]">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756] flex items-center justify-center">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Semantic Memory Bank
              </h2>
              <p className="text-zinc-400 text-xs mt-0.5">
                Query factual constraints, code patterns, and strategic insights collected during previous runs via Cosine Vector Search.
              </p>
            </div>
          </div>
        </div>
        
        <button 
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2.5 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Record New Memory</span>
        </button>
      </div>

      {/* Insert Memory Form */}
      {showForm && (
        <form onSubmit={handleAddMemory} className="glass-panel rounded-2xl p-6 space-y-4 border border-zinc-800 bg-[#18181b]">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div className="flex items-center gap-2 text-white font-bold text-xs uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#da7756]" />
              <span>Record New Knowledge Chunk</span>
            </div>
            <select 
              value={newCategory} 
              onChange={(e) => setNewCategory(e.target.value)}
              className="bg-[#121214] border border-zinc-800 rounded-lg px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-[#da7756]/60 cursor-pointer"
            >
              <option value="factual">Factual Constraint</option>
              <option value="insight">Strategic Insight</option>
              <option value="code">Code Pattern</option>
            </select>
          </div>

          <textarea 
            rows={3}
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder="Input key facts or observations you want the agents to recall in future tasks..."
            className="w-full bg-[#121214] border border-zinc-800 rounded-xl p-3.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 leading-relaxed resize-none"
          />

          <div className="flex justify-end gap-2.5 text-xs">
            <button 
              type="button" 
              onClick={() => setShowForm(false)} 
              className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-white font-semibold cursor-pointer"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={isInserting}
              className="px-5 py-2 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Save Knowledge Record</span>
            </button>
          </div>
        </form>
      )}

      {/* Query Filters */}
      <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
        {/* Search */}
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-zinc-500" />
          <input 
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search semantically inside recorded memories (e.g. 'rate limiter token bucket' or 'market CAGR')..."
            className="w-full bg-[#121214] border border-zinc-800 rounded-xl pl-10 pr-4 py-3 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 transition"
          />
        </div>
        
        {/* Category selection */}
        <div className="flex items-center gap-2 self-start md:self-auto select-none flex-wrap">
          {[
            { label: "All Categories", val: "" },
            { label: "Factual", val: "factual" },
            { label: "Insights", val: "insight" },
            { label: "Code Patterns", val: "code" }
          ].map((cat) => {
            const isSelected = selectedCategory === cat.val;
            return (
              <button
                key={cat.val}
                onClick={() => setSelectedCategory(cat.val)}
                className={`px-3.5 py-2 rounded-xl text-xs font-semibold border transition cursor-pointer ${
                  isSelected 
                    ? "bg-[#da7756]/15 text-white border-[#da7756]/40" 
                    : "border-zinc-800 bg-[#18181b] text-zinc-400 hover:text-white hover:border-zinc-700"
                }`}
              >
                {cat.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Memories Grid list */}
      <div className="space-y-4">
        {memories.length === 0 ? (
          <div className="text-center py-16 text-zinc-500 text-xs italic bg-[#141416] border border-zinc-800 rounded-2xl">
            No memories matched your semantic query. Execute a task to record agent observations automatically.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {memories.map((mem) => (
              <div 
                key={mem.id} 
                className="glass-panel-interactive border border-zinc-800 rounded-2xl p-5 flex flex-col justify-between space-y-4 relative bg-[#18181b]"
              >
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] uppercase font-bold text-zinc-400 bg-[#121214] border border-zinc-800 px-2 py-0.5 rounded-md">
                      {mem.category}
                    </span>
                    {mem.match_percentage && (
                      <span className="px-2.5 py-0.5 rounded-full bg-[#da7756]/15 border border-[#da7756]/30 text-[10px] font-bold text-[#da7756]">
                        🎯 {mem.match_percentage} Vector Match
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-200 leading-relaxed font-normal select-text whitespace-pre-wrap">
                    {mem.content}
                  </p>
                </div>
                
                <div className="flex items-center justify-between border-t border-zinc-800 pt-3 text-[10px] text-zinc-500 font-semibold">
                  <div className="flex items-center gap-1.5">
                    <Folder className="w-3.5 h-3.5 text-zinc-500" />
                    <span>Memory Node</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-zinc-500" />
                    <span>{new Date(mem.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
