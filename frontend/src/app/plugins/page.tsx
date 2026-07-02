"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PocketKnife, Puzzle, Download, ArrowUpRight, Search, Sparkles } from "lucide-react";
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
      
      {/* Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900 pb-6">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <PocketKnife className="w-6 h-6 text-blue-500" />
            <span>Workforce Plugins Directory</span>
          </h2>
          <p className="text-slate-400 text-xs mt-1">
            Plugins define the sequence of subtasks, custom prompt guidelines, and validation constraints that agents follow to accomplish a target goal.
          </p>
        </div>
      </div>

      {/* Grid: Active Plugins */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Installed Workforce Workflows
        </h3>
        
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="h-44 bg-slate-900/40 rounded-xl animate-pulse" />
            <div className="h-44 bg-slate-900/40 rounded-xl animate-pulse" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {plugins.map((p) => (
              <div 
                key={p.plugin_id}
                className="glass-panel border border-slate-800 rounded-xl p-6 flex flex-col justify-between hover:border-slate-700/60 transition duration-300 relative overflow-hidden group"
              >
                {/* Visual Accent */}
                <div className="absolute top-0 right-0 w-24 h-24 bg-blue-600/5 rounded-full blur-2xl pointer-events-none group-hover:bg-blue-600/10 transition" />
                
                <div className="space-y-3.5">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                        <Puzzle className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-sm text-slate-100">{p.name}</h4>
                        <span className="text-[9px] text-slate-500 font-mono block mt-0.5">ID: {p.plugin_id}</span>
                      </div>
                    </div>
                    
                    <span className="text-[9px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 px-2 py-0.5 rounded uppercase tracking-wider">
                      Active
                    </span>
                  </div>
                  
                  <p className="text-xs text-slate-400 leading-relaxed font-normal">{p.description}</p>
                </div>

                <div className="border-t border-slate-900/80 pt-4 mt-5 flex justify-between items-center text-xs">
                  <span className="text-slate-500 font-medium">Standard Workforce Flow</span>
                  <Link 
                    href={`/chat?plugin_id=${p.plugin_id}`}
                    className="text-blue-400 font-semibold flex items-center gap-1 hover:underline"
                  >
                    <span>Deploy Workspace</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Plugin Marketplace (Placeholder) */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Workforce Marketplace
          </h3>
        </div>
        
        <div className="glass-panel border border-slate-800/80 rounded-xl p-8 text-center max-w-3xl mx-auto space-y-4">
          <div className="w-12 h-12 bg-purple-500/10 rounded-full flex items-center justify-center text-purple-400 mx-auto glow-purple/20">
            <Download className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h4 className="font-semibold text-sm text-slate-200">Expand Your Automated Capabilities</h4>
            <p className="text-xs text-slate-400 mt-1.5 max-w-lg mx-auto leading-relaxed">
              Integrate plugins for Medical Report Analysis, Fraud Auditing, Document Intelligence, Business Strategy, and Resume Screening.
            </p>
          </div>
          <div className="pt-2">
            <button 
              disabled 
              className="px-4 py-2 bg-purple-600/20 text-purple-400 font-semibold text-xs border border-purple-500/20 rounded-lg cursor-not-allowed"
            >
              Marketplace Offline (MVP)
            </button>
          </div>
        </div>
      </div>

    </div>
  );
}
