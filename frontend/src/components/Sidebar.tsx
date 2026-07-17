"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { 
  LayoutDashboard, 
  MessageSquare, 
  BrainCircuit, 
  Cpu, 
  PocketKnife, 
  Radio,
  History
} from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

// Strip trailing /api to get base server URL for health checks
const HEALTH_URL = API_BASE_URL.endsWith("/api")
  ? API_BASE_URL.slice(0, -4) + "/health"
  : API_BASE_URL + "/health";


const NAV_ITEMS = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Workspace", href: "/chat", icon: MessageSquare },
  { label: "Launch History", href: "/recent", icon: History },
  { label: "Memory Bank", href: "/memory", icon: BrainCircuit },
  { label: "MCP Servers", href: "/mcp", icon: Cpu },
  { label: "Plugins", href: "/plugins", icon: PocketKnife },
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
    <aside className="w-64 border-r border-slate-800/80 bg-slate-950/80 backdrop-blur-xl flex flex-col h-screen sticky top-0 shrink-0">
      {/* Brand Logo Header */}
      <div className="p-6 border-b border-slate-800/50 flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center glow-primary">
          <Radio className="w-5 h-5 text-white animate-pulse" />
        </div>
        <div>
          <h1 className="font-semibold text-lg bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 leading-none">
            AgentForge
          </h1>
          <span className="text-[10px] text-slate-500 font-medium tracking-widest uppercase">
            Workforce v1.0
          </span>
        </div>
      </div>

      {/* Navigation list */}
      <nav className="flex-1 px-4 py-6 space-y-1.5">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3.5 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-blue-600/10 border-l-2 border-blue-500 text-blue-400"
                  : "text-slate-400 hover:text-white hover:bg-slate-900/60"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-blue-400" : "text-slate-400 group-hover:text-white"}`} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Health status footer */}
      <div className="p-5 border-t border-slate-800/50 flex items-center justify-between text-xs text-slate-500 font-medium">
        <span>System Core API</span>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              apiStatus === "healthy"
                ? "bg-emerald-500 pulse-emerald"
                : apiStatus === "connecting"
                ? "bg-amber-500 animate-pulse"
                : "bg-rose-500"
            }`}
          />
          <span className="capitalize">{apiStatus}</span>
        </div>
      </div>
    </aside>
  );
}
