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
    <html lang="en" className="h-full bg-[#121214] text-zinc-100 dark">
      <body className={`${inter.className} min-h-full flex overflow-hidden antialiased bg-[#121214] text-[#f4f4f5]`}>
        {/* Subtle Minimal Grid Pattern without glowing blur blobs */}
        <div className="fixed inset-0 bg-grid-pattern opacity-40 pointer-events-none z-0" />
        
        {/* Sidebar Navigation */}
        <Sidebar />
        
        {/* Main Content Area */}
        <main className="flex-1 flex flex-col h-screen overflow-y-auto relative z-10 bg-[#121214]">
          {children}
        </main>
      </body>
    </html>
  );
}
