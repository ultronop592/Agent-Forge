"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BrainCircuit, Search, Calendar, Folder, Plus, Check } from "lucide-react";

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
    <div className="p-8 max-w-5xl mx-auto space-y-8 w-full relative z-10">
      
      {/* Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900 pb-6">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <BrainCircuit className="w-6 h-6 text-blue-500" />
            <span>Semantic Memory Bank</span>
          </h2>
          <p className="text-slate-400 text-xs mt-1">
            Browse and query factual constraints, code patterns, and strategic outcomes collected during previous runs via Cosine Similarity Vector Search.
          </p>
        </div>
        
        <button 
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow transition"
        >
          <Plus className="w-4 h-4" />
          <span>Record New Memory</span>
        </button>
      </div>

      {/* Insert Memory Form */}
      {showForm && (
        <form onSubmit={handleAddMemory} className="glass-panel border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-900 pb-2.5">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">Record Learnings Block</h4>
            <select 
              value={newCategory} 
              onChange={(e) => setNewCategory(e.target.value)}
              className="bg-slate-950 border border-slate-800/80 rounded px-2.5 py-1 text-xs text-slate-400 focus:outline-none"
            >
              <option value="factual">Factual Record</option>
              <option value="insight">Strategic Insight</option>
              <option value="code">Code Pattern</option>
            </select>
          </div>
          <textarea 
            rows={3}
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder="Input key facts or observations you want the agents to recall in future tasks..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-300 focus:outline-none focus:border-blue-500 leading-relaxed"
          />
          <div className="flex justify-end gap-2 text-xs">
            <button 
              type="button" 
              onClick={() => setShowForm(false)} 
              className="px-3.5 py-1.5 rounded hover:bg-slate-900 text-slate-400 font-medium"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={isInserting}
              className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center gap-1.5 shadow"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Save Record</span>
            </button>
          </div>
        </form>
      )}

      {/* Query Filters */}
      <div className="flex flex-col md:flex-row gap-4 items-center">
        {/* Search */}
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-500" />
          <input 
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search semantically inside recorded memories (e.g. 'rate limiter token bucket' or 'SWOT analysis')..."
            className="w-full bg-slate-950 border border-slate-850/80 rounded-lg pl-10 pr-4 py-3 text-xs text-slate-300 focus:outline-none focus:border-blue-500"
          />
        </div>
        
        {/* Category selection */}
        <div className="flex items-center gap-1.5 self-start md:self-auto select-none flex-wrap">
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
                className={`px-3.5 py-2 rounded-lg text-xs font-semibold border transition ${
                  isSelected 
                    ? "bg-slate-900 text-blue-400 border-blue-500/30" 
                    : "border-transparent text-slate-400 hover:text-slate-350 hover:bg-slate-900/60"
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
          <div className="text-center py-16 text-slate-500 text-xs italic bg-slate-950 border border-slate-900 rounded-xl">
            No memories matched your semantic query. Execute a task to record agent observations automatically.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {memories.map((mem) => (
              <div 
                key={mem.id}
                className="glass-panel border border-slate-800/80 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700/80 transition duration-300 space-y-4 relative"
              >
                <div className="space-y-2">
                  {mem.match_percentage && (
                    <div className="flex justify-end">
                      <span className="px-2 py-0.5 rounded-full bg-blue-950/80 border border-blue-700/40 text-[10px] font-bold text-blue-400">
                        🎯 {mem.match_percentage} Vector Match
                      </span>
                    </div>
                  )}
                  <p className="text-xs text-slate-300 leading-relaxed font-normal select-text whitespace-pre-wrap">
                    {mem.content}
                  </p>
                </div>
                
                <div className="flex items-center justify-between border-t border-slate-900 pt-3 text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                  <div className="flex items-center gap-1.5">
                    <Folder className="w-3.5 h-3.5 text-slate-600" />
                    <span>{mem.category}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-600" />
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
