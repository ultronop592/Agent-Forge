"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { 
  LayoutDashboard, 
  Layers, 
  BrainCircuit, 
  Cpu, 
  PocketKnife, 
  History,
  Activity,
  Bot
} from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

// Strip trailing /api to get base server URL for health checks
const HEALTH_URL = API_BASE_URL.endsWith("/api")
  ? API_BASE_URL.slice(0, -4) + "/health"
  : API_BASE_URL + "/health";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, badge: null },
  { label: "AI Workspace", href: "/chat", icon: Layers, badge: "Live" },
  { label: "Launch History", href: "/recent", icon: History, badge: null },
  { label: "Memory Bank", href: "/memory", icon: BrainCircuit, badge: null },
  { label: "MCP Control", href: "/mcp", icon: Cpu, badge: "JSON-RPC" },
  { label: "Workforce Plugins", href: "/plugins", icon: PocketKnife, badge: null },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [apiStatus, setApiStatus] = useState<"connecting" | "healthy" | "offline">("connecting");

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(HEALTH_URL);
        if (res.ok) {
          setApiStatus("healthy");
        } else {
          setApiStatus("offline");
        }
      } catch (e) {
        setApiStatus("offline");
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 8000);
    return () => clearInterval(interval);
  }, []);

  return (
    <aside className="w-64 border-r border-zinc-800/80 bg-[#161619] flex flex-col h-screen sticky top-0 shrink-0 select-none z-20">
      {/* Brand Logo Header */}
      <div className="p-5 border-b border-zinc-800/80 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-[#da7756] flex items-center justify-center group-hover:scale-105 transition-transform">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h1 className="font-bold text-base text-white tracking-tight leading-none">
                AgentForge
              </h1>
              <span className="w-1.5 h-1.5 rounded-full bg-[#da7756]" />
            </div>
            <span className="text-[10px] font-semibold text-[#da7756] tracking-wider uppercase block mt-1">
              Autonomous Workforce
            </span>
          </div>
        </Link>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-3 py-5 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-500">
          Navigation
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 group relative ${
                isActive
                  ? "bg-[#da7756]/12 text-white border border-[#da7756]/30"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-800/60 border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-1 rounded-lg transition-colors ${
                  isActive 
                    ? "bg-[#da7756]/20 text-[#da7756]" 
                    : "text-zinc-400 group-hover:text-[#da7756] group-hover:bg-zinc-800/50"
                }`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span>{item.label}</span>
              </div>

              {item.badge && (
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                  isActive
                    ? "bg-[#da7756]/20 text-[#da7756] border border-[#da7756]/30"
                    : "bg-zinc-800 text-zinc-400 group-hover:text-zinc-300"
                }`}>
                  {item.badge}
                </span>
              )}

              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-r-full bg-[#da7756]" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Health Status Footer */}
      <div className="p-4 border-t border-zinc-800/80 bg-[#141416]">
        <div className="p-3 rounded-xl bg-[#18181b] border border-zinc-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-zinc-500" />
            <span className="text-[11px] font-medium text-zinc-300">System Core API</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                apiStatus === "healthy"
                  ? "bg-emerald-400"
                  : apiStatus === "connecting"
                  ? "bg-amber-400 animate-pulse"
                  : "bg-rose-500"
              }`}
            />
            <span className={`text-[10px] font-bold uppercase tracking-wider ${
              apiStatus === "healthy" ? "text-emerald-400" : apiStatus === "connecting" ? "text-amber-400" : "text-rose-400"
            }`}>
              {apiStatus}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
