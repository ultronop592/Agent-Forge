"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PocketKnife, Puzzle, Download, ArrowUpRight, Search, Sparkles, Rocket } from "lucide-react";
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
    <div className="p-8 max-w-6xl mx-auto space-y-9 w-full relative z-10">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-sky-500/15 border border-sky-500/30 text-sky-400 flex items-center justify-center">
              <PocketKnife className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Workforce Plugins Directory
              </h2>
              <p className="text-slate-400 text-xs mt-0.5">
                Plugins define the sequence of subtasks, custom agent prompts, and verification constraints that execute complex goals.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Active Plugins */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Installed Workflow Blueprints
          </h3>
          <span className="text-[10px] text-slate-500 font-semibold">{plugins.length} Available</span>
        </div>
        
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="h-44 bg-[#080b12] border border-slate-800 rounded-2xl animate-pulse" />
            <div className="h-44 bg-[#080b12] border border-slate-800 rounded-2xl animate-pulse" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {plugins.map((p) => (
              <div 
                key={p.plugin_id}
                className="glass-panel-interactive border border-slate-800/90 rounded-2xl p-6 flex flex-col justify-between relative overflow-hidden group"
              >
                <div className="space-y-3.5">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400">
                        <Puzzle className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="font-bold text-sm text-white group-hover:text-sky-300 transition-colors">{p.name}</h4>
                        <span className="text-[10px] text-slate-400 font-mono block mt-0.5">ID: {p.plugin_id}</span>
                      </div>
                    </div>
                    
                    <span className="text-[9px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full uppercase tracking-wider">
                      Active
                    </span>
                  </div>
                  
                  <p className="text-xs text-slate-300 leading-relaxed font-normal">{p.description}</p>
                </div>

                <div className="border-t border-slate-800/80 pt-4 mt-5 flex justify-between items-center text-xs">
                  <span className="text-slate-500 font-medium">Standard Workforce Flow</span>
                  <Link 
                    href={`/chat?plugin_id=${p.plugin_id}`}
                    className="text-sky-400 hover:text-sky-300 font-semibold flex items-center gap-1 group-hover:underline"
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
          <Sparkles className="w-4 h-4 text-sky-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Workforce Plugin Marketplace
          </h3>
        </div>
        
        <div className="glass-panel-elevated border border-slate-800 rounded-2xl p-8 text-center max-w-3xl mx-auto space-y-4">
          <div className="w-12 h-12 bg-sky-500/15 border border-sky-500/30 rounded-2xl flex items-center justify-center text-sky-400 mx-auto glow-primary">
            <Download className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h4 className="font-bold text-sm text-white">Expand Your Autonomous Workflow Library</h4>
            <p className="text-xs text-slate-400 mt-1.5 max-w-lg mx-auto leading-relaxed">
              Plug-and-play workflows for Market Competitive Analysis, Python Architecture Refactoring, Real-time Web Scraping, and Document Intelligence.
            </p>
          </div>
          <div className="pt-2">
            <span className="inline-block px-4 py-1.5 bg-sky-500/10 text-sky-400 font-bold text-[10px] uppercase tracking-wider border border-sky-500/20 rounded-full">
              Enterprise Ecosystem Ready
            </span>
          </div>
        </div>
      </div>

    </div>
  );
}
