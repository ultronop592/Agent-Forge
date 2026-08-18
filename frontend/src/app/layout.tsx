import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Sidebar from "@/components/Sidebar";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "AgentForge — Autonomous AI Workforce Platform",
  description: "Enterprise-grade multi-agent autonomous workforce platform for research, reasoning, code synthesis, and verified execution.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full bg-[#07090e] text-slate-100 dark">
      <body className={`${inter.className} min-h-full flex overflow-hidden antialiased bg-[#07090e]`}>
        {/* Subtle Ambient Radial Lighting */}
        <div className="fixed inset-0 bg-grid-pattern opacity-30 pointer-events-none z-0" />
        <div className="fixed top-[-100px] left-[20%] w-[600px] h-[500px] bg-sky-500/8 rounded-full blur-[140px] pointer-events-none z-0" />
        <div className="fixed bottom-[-100px] right-[10%] w-[500px] h-[500px] bg-blue-600/6 rounded-full blur-[140px] pointer-events-none z-0" />
        
        {/* Sidebar Navigation */}
        <Sidebar />
        
        {/* Main Content Area */}
        <main className="flex-1 flex flex-col h-screen overflow-y-auto relative z-10">
          {children}
        </main>
      </body>
    </html>
  );
}
