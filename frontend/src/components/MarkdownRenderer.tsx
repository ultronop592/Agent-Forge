"use client";

import React from "react";

interface MarkdownRendererProps {
  content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content) return <span className="text-slate-500 italic">No content generated.</span>;

  // Simple token-based markdown parser
  const renderLine = (line: string, index: number) => {
    const trimmed = line.trim();

    // Check for Headers
    if (trimmed.startsWith("# ")) {
      return (
        <h1 key={index} className="text-2xl font-bold text-white mt-6 mb-3 tracking-tight">
          {trimmed.slice(2)}
        </h1>
      );
    }
    if (trimmed.startsWith("## ")) {
      return (
        <h2 key={index} className="text-xl font-semibold text-slate-100 mt-5 mb-2.5 border-b border-slate-800 pb-1">
          {trimmed.slice(3)}
        </h2>
      );
    }
    if (trimmed.startsWith("### ")) {
      return (
        <h3 key={index} className="text-lg font-medium text-slate-200 mt-4 mb-2">
          {trimmed.slice(4)}
        </h3>
      );
    }

    // Check for Blockquotes/Alerts
    if (trimmed.startsWith("> ")) {
      const quoteText = trimmed.slice(2).trim();
      if (quoteText.startsWith("[!NOTE]")) {
        return (
          <div key={index} className="my-4 p-4 rounded-lg bg-blue-500/10 border-l-4 border-blue-500 text-blue-300 text-sm">
            <span className="font-semibold block mb-1">NOTE</span>
            {quoteText.replace("[!NOTE]", "").trim()}
          </div>
        );
      }
      if (quoteText.startsWith("[!WARNING]")) {
        return (
          <div key={index} className="my-4 p-4 rounded-lg bg-amber-500/10 border-l-4 border-amber-500 text-amber-300 text-sm">
            <span className="font-semibold block mb-1">WARNING</span>
            {quoteText.replace("[!WARNING]", "").trim()}
          </div>
        );
      }
      if (quoteText.startsWith("[!IMPORTANT]")) {
        return (
          <div key={index} className="my-4 p-4 rounded-lg bg-emerald-500/10 border-l-4 border-emerald-500 text-emerald-300 text-sm">
            <span className="font-semibold block mb-1">IMPORTANT</span>
            {quoteText.replace("[!IMPORTANT]", "").trim()}
          </div>
        );
      }
      return (
        <blockquote key={index} className="border-l-4 border-slate-700 pl-4 py-1 my-3 text-slate-400 italic bg-slate-900/20 rounded-r-md">
          {quoteText}
        </blockquote>
      );
    }

    // Check for Lists
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      return (
        <li key={index} className="ml-5 list-disc text-slate-300 my-1 font-normal">
          {renderInlineFormatting(trimmed.slice(2))}
        </li>
      );
    }

    // Check for numbered lists
    const numMatch = trimmed.match(/^(\d+)\.\s(.*)/);
    if (numMatch) {
      return (
        <li key={index} className="ml-5 list-decimal text-slate-300 my-1 font-normal">
          {renderInlineFormatting(numMatch[2])}
        </li>
      );
    }

    // Empty Lines
    if (trimmed === "") {
      return <div key={index} className="h-2" />;
    }

    // Normal paragraph
    return (
      <p key={index} className="text-slate-300 leading-relaxed my-2 text-sm">
        {renderInlineFormatting(line)}
      </p>
    );
  };

  // Renders bold, code, and links in lines
  const renderInlineFormatting = (text: string) => {
    const parts: React.ReactNode[] = [];
    let currentIdx = 0;
    
    // Bold, Code, Link Matchers
    const regex = /(\*\*.*?\*\*|`.*?`|\[.*?\]\(.*?\))/g;
    const matches = Array.from(text.matchAll(regex));
    
    if (matches.length === 0) {
      return text;
    }
    
    matches.forEach((match, mIdx) => {
      const matchText = match[0];
      const matchIndex = match.index || 0;
      
      // Push text before match
      if (matchIndex > currentIdx) {
        parts.push(text.slice(currentIdx, matchIndex));
      }
      
      if (matchText.startsWith("**") && matchText.endsWith("**")) {
        parts.push(<strong key={`b-${mIdx}`} className="font-semibold text-white">{matchText.slice(2, -2)}</strong>);
      } else if (matchText.startsWith("`") && matchText.endsWith("`")) {
        parts.push(
          <code key={`c-${mIdx}`} className="bg-slate-900/80 px-1.5 py-0.5 rounded text-rose-400 font-mono text-xs border border-slate-800">
            {matchText.slice(1, -1)}
          </code>
        );
      } else if (matchText.startsWith("[") && matchText.includes("](")) {
        const title = matchText.slice(1, matchText.indexOf("]"));
        const url = matchText.slice(matchText.indexOf("](") + 2, -1);
        parts.push(
          <a key={`l-${mIdx}`} href={url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
            {title}
          </a>
        );
      }
      
      currentIdx = matchIndex + matchText.length;
    });
    
    if (currentIdx < text.length) {
      parts.push(text.slice(currentIdx));
    }
    
    return parts;
  };

  // Group lines and render code blocks
  const renderBlocks = () => {
    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    
    let inCodeBlock = false;
    let codeContent: string[] = [];
    let codeLang = "text";
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim().startsWith("```")) {
        if (inCodeBlock) {
          // Close Code Block
          elements.push(
            <pre key={`code-${i}`} className="bg-slate-950 border border-slate-800/80 p-4 rounded-lg my-4 font-mono text-xs text-slate-300 overflow-x-auto glow-primary/5">
              <div className="flex justify-between items-center text-[10px] text-slate-500 border-b border-slate-900 pb-2 mb-3 uppercase tracking-wider">
                <span>{codeLang} Code Block</span>
                <span className="lowercase text-[9px]">read-only</span>
              </div>
              <code>{codeContent.join("\n")}</code>
            </pre>
          );
          codeContent = [];
          inCodeBlock = false;
        } else {
          // Open Code Block
          inCodeBlock = true;
          codeLang = line.trim().slice(3) || "text";
        }
      } else {
        if (inCodeBlock) {
          codeContent.push(line);
        } else {
          elements.push(renderLine(line, i));
        }
      }
    }
    return elements;
  };

  return <div className="space-y-0.5">{renderBlocks()}</div>;
}
