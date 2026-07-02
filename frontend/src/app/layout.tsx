import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Sidebar from "@/components/Sidebar";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AgentForge - Multi-Agent Collaborative AI Workforce",
  description: "A collaborative AI workforce that researches, reasons, plans, executes, verifies, and continuously improves complex real-world tasks.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full bg-slate-950 text-slate-100 dark">
      <body className={`${inter.className} min-h-full flex overflow-hidden`}>
        {/* Decorative Grid Overlay background */}
        <div className="absolute inset-0 bg-grid-pattern opacity-40 pointer-events-none z-0" />
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-600/5 rounded-full blur-[120px] pointer-events-none z-0" />
        <div className="absolute bottom-0 left-64 w-[500px] h-[500px] bg-purple-600/5 rounded-full blur-[120px] pointer-events-none z-0" />
        
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
