"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PocketKnife, Puzzle, Download, ArrowUpRight, Sparkles } from "lucide-react";
import Link from "next/link";

interface Plugin {
  plugin_id: string;
  name: string;
  description: string;
}

export default function PluginsDirectory() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadPlugins = async () => {
      try {
        const data = await api.getPlugins();
        setPlugins(data);
      } catch (e) {
        console.error("Failed to load plugins:", e);
      } finally {
        setLoading(false);
      }
    };
    loadPlugins();
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-9 w-full relative z-10 bg-[#121214] text-[#f4f4f5]">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756] flex items-center justify-center">
              <PocketKnife className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Workforce Plugins Directory
              </h2>
              <p className="text-zinc-400 text-xs mt-0.5">
                Plugins define the sequence of subtasks, custom agent prompts, and verification constraints that execute complex goals.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Active Plugins */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-300">
            Installed Workflow Blueprints
          </h3>
          <span className="text-[10px] text-zinc-500 font-semibold">{plugins.length} Available</span>
        </div>
        
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="h-44 bg-[#141416] border border-zinc-800 rounded-2xl animate-pulse" />
            <div className="h-44 bg-[#141416] border border-zinc-800 rounded-2xl animate-pulse" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {plugins.map((p) => (
              <div 
                key={p.plugin_id}
                className="glass-panel-interactive border border-zinc-800 rounded-2xl p-6 flex flex-col justify-between relative overflow-hidden group bg-[#18181b]"
              >
                <div className="space-y-3.5">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-[#da7756]/15 border border-[#da7756]/30 flex items-center justify-center text-[#da7756]">
                        <Puzzle className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="font-bold text-sm text-white group-hover:text-[#da7756] transition-colors">{p.name}</h4>
                        <span className="text-[10px] text-zinc-400 font-mono block mt-0.5">ID: {p.plugin_id}</span>
                      </div>
                    </div>
                    
                    <span className="text-[9px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full uppercase tracking-wider">
                      Active
                    </span>
                  </div>
                  
                  <p className="text-xs text-zinc-300 leading-relaxed font-normal">{p.description}</p>
                </div>

                <div className="border-t border-zinc-800 pt-4 mt-5 flex justify-between items-center text-xs">
                  <span className="text-zinc-500 font-medium">Standard Workforce Flow</span>
                  <Link 
                    href={`/chat?plugin_id=${p.plugin_id}`}
                    className="text-[#da7756] hover:text-[#e08569] font-semibold flex items-center gap-1 group-hover:underline"
                  >
                    <span>Deploy Workspace</span>
                    <ArrowUpRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Plugin Marketplace (Roadmap Preview) */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#da7756]" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-300">
            Workforce Plugin Marketplace
          </h3>
        </div>
        
        <div className="glass-panel border border-zinc-800 rounded-2xl p-8 text-center max-w-3xl mx-auto space-y-4 bg-[#18181b]">
          <div className="w-12 h-12 bg-[#da7756]/10 border border-[#da7756]/20 rounded-2xl flex items-center justify-center text-[#da7756] mx-auto">
            <Download className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-sm text-white">Expand Your Autonomous Workflow Library</h4>
            <p className="text-xs text-zinc-400 mt-1.5 max-w-lg mx-auto leading-relaxed">
              Plug-and-play workflows for Market Competitive Analysis, Python Architecture Refactoring, Real-time Web Scraping, and Document Intelligence.
            </p>
          </div>
          <div className="pt-2">
            <span className="inline-block px-4 py-1.5 bg-[#da7756]/10 text-[#da7756] font-bold text-[10px] uppercase tracking-wider border border-[#da7756]/20 rounded-full">
              Enterprise Ecosystem Ready
            </span>
          </div>
        </div>
      </div>

    </div>
  );
}
