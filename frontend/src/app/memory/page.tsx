"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { api } from "@/lib/api";
import { 
  BrainCircuit, 
  Search, 
  Calendar, 
  Plus, 
  Check, 
  Sparkles, 
  Trash2, 
  X, 
  Copy, 
  CheckCheck, 
  AlertTriangle,
  RotateCw,
  SlidersHorizontal,
  FolderOpen
} from "lucide-react";

interface Memory {
  id: string;
  category: string;
  content: string;
  created_at: string;
  match_percentage?: string;
  similarity_score?: number;
}

interface MemoryStats {
  total: number;
  categories: {
    all: number;
    factual: number;
    insight: number;
    code: number;
    other: number;
  };
}

export default function MemoryBank() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [stats, setStats] = useState<MemoryStats>({
    total: 0,
    categories: { all: 0, factual: 0, insight: 0, code: 0, other: 0 }
  });
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [searchMode, setSearchMode] = useState<"vector" | "keyword">("vector");
  
  // Custom memory insertion form
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("factual");
  const [isInserting, setIsInserting] = useState(false);
  const [showForm, setShowForm] = useState(false);

  // Deletion states
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBatchDeleting, setIsBatchDeleting] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const showToast = (message: string, type: "success" | "error" = "success") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3500);
  };

  const loadStats = useCallback(async () => {
    try {
      const data = await api.getMemoryStats();
      if (data && data.categories) {
        setStats(data);
      }
    } catch (e) {
      console.error("Failed to load memory stats:", e);
    }
  }, []);

  const loadMemories = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getMemory(searchQuery, selectedCategory);
      setMemories(Array.isArray(data) ? data : []);
      loadStats();
    } catch (e) {
      console.error("Failed to fetch memories:", e);
      showToast("Error connecting to Memory Bank", "error");
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedCategory, loadStats]);

  useEffect(() => {
    const handler = setTimeout(() => {
      loadMemories();
    }, 200);
    return () => clearTimeout(handler);
  }, [searchQuery, selectedCategory, loadMemories]);

  // Handle Add Memory
  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    
    setIsInserting(true);
    try {
      await api.addMemory(newContent.trim(), newCategory);
      setNewContent("");
      setShowForm(false);
      showToast("Knowledge node recorded successfully");
      await loadMemories();
    } catch (err) {
      console.error("Failed to add memory:", err);
      showToast("Failed to save memory node", "error");
    } finally {
      setIsInserting(false);
    }
  };

  // Handle Delete Single Memory
  const handleDeleteMemory = async (id: string) => {
    setDeletingId(id);
    try {
      await api.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      setConfirmDeleteId(null);
      showToast("Memory node deleted");
      loadStats();
    } catch (err) {
      console.error("Failed to delete memory:", err);
      showToast("Failed to delete memory node", "error");
    } finally {
      setDeletingId(null);
    }
  };

  // Handle Batch Delete Selected
  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    setIsBatchDeleting(true);
    try {
      const promises = Array.from(selectedIds).map((id) => api.deleteMemory(id));
      await Promise.all(promises);
      setMemories((prev) => prev.filter((m) => !selectedIds.has(m.id)));
      showToast(`Deleted ${selectedIds.size} knowledge records`);
      setSelectedIds(new Set());
      loadStats();
    } catch (err) {
      console.error("Failed batch delete:", err);
      showToast("Failed to complete batch delete", "error");
    } finally {
      setIsBatchDeleting(false);
    }
  };

  // Toggle Selection
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === memories.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(memories.map((m) => m.id)));
    }
  };

  // Copy to clipboard
  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Filter category styling helper
  const getCategoryBadge = (cat: string) => {
    switch (cat.toLowerCase()) {
      case "factual":
        return {
          bg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
          dot: "bg-emerald-400",
          label: "Factual Constraint"
        };
      case "insight":
        return {
          bg: "bg-purple-500/10 border-purple-500/30 text-purple-300",
          dot: "bg-purple-400",
          label: "Strategic Insight"
        };
      case "code":
        return {
          bg: "bg-blue-500/10 border-blue-500/30 text-blue-400",
          dot: "bg-blue-400",
          label: "Code Pattern"
        };
      default:
        return {
          bg: "bg-zinc-800 border-zinc-700 text-zinc-300",
          dot: "bg-zinc-400",
          label: cat
        };
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-7 w-full relative z-10 bg-[#121214] text-[#f4f4f5]">
      {/* Toast Notification */}
      {notification && (
        <div 
          className={`fixed top-6 right-6 z-50 px-4 py-2.5 rounded-xl border text-xs font-semibold shadow-2xl flex items-center gap-2 backdrop-blur-md transition-all ${
            notification.type === "success"
              ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-200"
              : "bg-rose-950/80 border-rose-500/50 text-rose-200"
          }`}
        >
          {notification.type === "success" ? (
            <Check className="w-4 h-4 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          )}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756] flex items-center justify-center shrink-0">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-white tracking-tight">
                  Semantic Memory Bank
                </h1>
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-md bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756]">
                  {stats.total} {stats.total === 1 ? "Node" : "Nodes"}
                </span>
              </div>
              <p className="text-zinc-400 text-xs mt-1">
                Filter, search, inspect, and delete institutional memories collected across agent reasoning loops.
              </p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2.5 self-start md:self-auto">
          <button
            onClick={() => loadMemories()}
            className="p-2.5 rounded-xl border border-zinc-800 bg-[#18181b] hover:bg-zinc-800 text-zinc-400 hover:text-white transition cursor-pointer"
            title="Refresh memories"
          >
            <RotateCw className={`w-4 h-4 ${loading ? "animate-spin text-[#da7756]" : ""}`} />
          </button>
          
          <button 
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2.5 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white text-xs font-bold flex items-center gap-2 transition cursor-pointer shadow-lg shadow-[#da7756]/10"
          >
            <Plus className="w-4 h-4" />
            <span>Record New Memory</span>
          </button>
        </div>
      </div>

      {/* Insert Memory Form */}
      {showForm && (
        <form onSubmit={handleAddMemory} className="rounded-2xl p-6 space-y-4 border border-[#da7756]/30 bg-[#18181b]/95 shadow-xl">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div className="flex items-center gap-2 text-white font-bold text-xs uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#da7756]" />
              <span>Record New Knowledge Chunk</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-zinc-400">Category:</span>
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
          </div>

          <textarea 
            rows={3}
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder="Input key facts, architectural constraints, or algorithmic patterns you want agents to recall in future tasks..."
            className="w-full bg-[#121214] border border-zinc-800 rounded-xl p-3.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 leading-relaxed resize-none"
            autoFocus
          />

          <div className="flex justify-end gap-2.5 text-xs">
            <button 
              type="button" 
              onClick={() => setShowForm(false)} 
              className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-white font-semibold cursor-pointer transition"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={isInserting || !newContent.trim()}
              className="px-5 py-2 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold flex items-center gap-1.5 transition cursor-pointer"
            >
              {isInserting ? (
                <>
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Embedding...</span>
                </>
              ) : (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Save Knowledge Record</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* Query Search & Filter Bar */}
      <div className="space-y-3.5">
        <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
          {/* Search Box */}
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-zinc-500" />
            <input 
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search semantically (e.g. 'rate limiter token bucket', 'PostgreSQL pgvector', or 'market CAGR')..."
              className="w-full bg-[#161619] border border-zinc-800 rounded-xl pl-10 pr-10 py-3 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 transition"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-3 p-0.5 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition cursor-pointer"
                title="Clear search"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Batch Delete action if items are selected */}
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2 self-start md:self-auto shrink-0 bg-rose-950/40 border border-rose-900/60 rounded-xl px-3 py-1.5">
              <span className="text-[11px] text-rose-300 font-semibold">
                {selectedIds.size} selected
              </span>
              <button
                onClick={handleBatchDelete}
                disabled={isBatchDeleting}
                className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-[11px] font-bold flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
              >
                <Trash2 className="w-3 h-3" />
                <span>{isBatchDeleting ? "Deleting..." : "Delete Selected"}</span>
              </button>
            </div>
          )}
        </div>
        
        {/* Category selection pills with count badges */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 select-none flex-wrap">
            {[
              { label: "All Categories", val: "", count: stats.categories.all },
              { label: "Factual Constraints", val: "factual", count: stats.categories.factual },
              { label: "Strategic Insights", val: "insight", count: stats.categories.insight },
              { label: "Code Patterns", val: "code", count: stats.categories.code }
            ].map((cat) => {
              const isSelected = selectedCategory === cat.val;
              return (
                <button
                  key={cat.val}
                  onClick={() => setSelectedCategory(cat.val)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition cursor-pointer flex items-center gap-2 ${
                    isSelected 
                      ? "bg-[#da7756]/15 text-white border-[#da7756]/40" 
                      : "border-zinc-800 bg-[#161619] text-zinc-400 hover:text-white hover:border-zinc-700"
                  }`}
                >
                  <span>{cat.label}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-md font-bold ${
                    isSelected 
                      ? "bg-[#da7756]/20 text-[#da7756]" 
                      : "bg-zinc-800 text-zinc-500"
                  }`}>
                    {cat.count}
                  </span>
                </button>
              );
            })}
          </div>

          {memories.length > 0 && (
            <div className="flex items-center gap-2 text-xs text-zinc-400">
              <button
                onClick={selectAll}
                className="text-[11px] text-zinc-400 hover:text-white transition cursor-pointer underline underline-offset-4"
              >
                {selectedIds.size === memories.length ? "Deselect All" : "Select All"}
              </button>
              <span className="text-zinc-600">|</span>
              <span className="text-[11px] text-zinc-500">
                Showing {memories.length} {memories.length === 1 ? "record" : "records"}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Memories Grid list */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-20 text-zinc-500 text-xs flex flex-col items-center gap-3 bg-[#161619]/50 border border-zinc-800/80 rounded-2xl">
            <RotateCw className="w-5 h-5 animate-spin text-[#da7756]" />
            <span>Scanning memory bank vector index...</span>
          </div>
        ) : memories.length === 0 ? (
          <div className="text-center py-16 px-4 text-zinc-400 text-xs bg-[#161619] border border-zinc-800 rounded-2xl flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-zinc-800/60 border border-zinc-700/60 flex items-center justify-center text-zinc-500">
              <FolderOpen className="w-6 h-6" />
            </div>
            <div>
              <p className="font-semibold text-zinc-300">No knowledge records found</p>
              <p className="text-zinc-500 text-[11px] mt-0.5">
                {searchQuery 
                  ? `No memories matched "${searchQuery}". Try different keywords or switch categories.`
                  : "Execute a task in the AI Workspace or record a new memory node above to populate institutional knowledge."
                }
              </p>
            </div>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="px-3.5 py-1.5 rounded-xl border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-white text-xs font-semibold transition cursor-pointer"
              >
                Clear Search Query
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {memories.map((mem) => {
              const badge = getCategoryBadge(mem.category);
              const isSelected = selectedIds.has(mem.id);
              const isDeleting = deletingId === mem.id;
              const isConfirming = confirmDeleteId === mem.id;

              return (
                <div 
                  key={mem.id} 
                  className={`border rounded-2xl p-5 flex flex-col justify-between space-y-4 relative transition-all duration-200 ${
                    isSelected 
                      ? "border-[#da7756]/50 bg-[#1e1b19]/90 ring-1 ring-[#da7756]/30" 
                      : "border-zinc-800/90 bg-[#161619] hover:border-zinc-700"
                  }`}
                >
                  <div className="space-y-3">
                    {/* Header Row: Category + Similarity + Actions */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {/* Checkbox */}
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(mem.id)}
                          className="w-3.5 h-3.5 rounded border-zinc-700 bg-[#121214] text-[#da7756] focus:ring-0 focus:ring-offset-0 cursor-pointer accent-[#da7756]"
                        />
                        <span className={`text-[10px] uppercase font-bold border px-2 py-0.5 rounded-md flex items-center gap-1.5 ${badge.bg}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
                          <span>{badge.label}</span>
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {mem.match_percentage && (
                          <span className="px-2 py-0.5 rounded-full bg-[#da7756]/15 border border-[#da7756]/30 text-[10px] font-bold text-[#da7756]">
                            🎯 {mem.match_percentage} Match
                          </span>
                        )}

                        {/* Copy Button */}
                        <button
                          onClick={() => handleCopy(mem.id, mem.content)}
                          className="p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-zinc-800 transition cursor-pointer"
                          title="Copy memory content"
                        >
                          {copiedId === mem.id ? (
                            <CheckCheck className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>

                        {/* Delete Button */}
                        <button
                          onClick={() => setConfirmDeleteId(isConfirming ? null : mem.id)}
                          className={`p-1.5 rounded-lg transition cursor-pointer ${
                            isConfirming 
                              ? "bg-rose-500/20 text-rose-400" 
                              : "text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10"
                          }`}
                          title="Delete memory node"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Inline Delete Confirmation Popover */}
                    {isConfirming && (
                      <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-900/60 text-xs flex items-center justify-between gap-3 animate-in fade-in duration-150">
                        <div className="flex items-center gap-2 text-rose-200 text-[11px]">
                          <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                          <span>Delete this knowledge record?</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => setConfirmDeleteId(null)}
                            className="px-2.5 py-1 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-[10px] font-semibold cursor-pointer"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleDeleteMemory(mem.id)}
                            disabled={isDeleting}
                            className="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-[10px] font-bold cursor-pointer disabled:opacity-50"
                          >
                            {isDeleting ? "Deleting..." : "Confirm Delete"}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Content */}
                    <p className="text-xs text-zinc-200 leading-relaxed font-normal select-text whitespace-pre-wrap">
                      {mem.content}
                    </p>
                  </div>
                  
                  {/* Footer Row: ID & Timestamp */}
                  <div className="flex items-center justify-between border-t border-zinc-800/80 pt-3 text-[10px] text-zinc-500 font-semibold">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-zinc-600">ID: {mem.id.slice(0, 8)}...</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3 h-3 text-zinc-500" />
                      <span>{mem.created_at ? new Date(mem.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "Recent"}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
