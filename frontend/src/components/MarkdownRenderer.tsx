"use client";

import React from "react";

interface MarkdownRendererProps {
  content: string;
}

// ---------------------------------------------------------------------------
// Inline formatting – bold, italic, strikethrough, inline-code, links
// ---------------------------------------------------------------------------
function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let cur = 0;

  const regex =
    /(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\)|~~.*?~~)/g;
  const matches = Array.from(text.matchAll(regex));

  if (matches.length === 0) return text;

  matches.forEach((m, mIdx) => {
    const raw = m[0];
    const idx = m.index ?? 0;

    if (idx > cur) parts.push(text.slice(cur, idx));

    if (raw.startsWith("***") && raw.endsWith("***")) {
      parts.push(
        <strong key={mIdx}>
          <em>{raw.slice(3, -3)}</em>
        </strong>
      );
    } else if (raw.startsWith("**") && raw.endsWith("**")) {
      parts.push(
        <strong key={mIdx} className="font-semibold text-white">
          {raw.slice(2, -2)}
        </strong>
      );
    } else if (raw.startsWith("*") && raw.endsWith("*")) {
      parts.push(
        <em key={mIdx} className="italic text-zinc-300">
          {raw.slice(1, -1)}
        </em>
      );
    } else if (raw.startsWith("~~") && raw.endsWith("~~")) {
      parts.push(
        <del key={mIdx} className="line-through text-zinc-500">
          {raw.slice(2, -2)}
        </del>
      );
    } else if (raw.startsWith("`") && raw.endsWith("`")) {
      parts.push(
        <code
          key={mIdx}
          className="bg-zinc-800/80 px-1.5 py-0.5 rounded text-[#da7756] font-mono text-xs border border-zinc-700"
        >
          {raw.slice(1, -1)}
        </code>
      );
    } else if (raw.startsWith("[") && raw.includes("](")) {
      const title = raw.slice(1, raw.indexOf("]"));
      const url = raw.slice(raw.indexOf("](") + 2, -1);
      parts.push(
        <a
          key={mIdx}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#da7756] hover:text-[#e08569] hover:underline transition-colors"
        >
          {title}
        </a>
      );
    }

    cur = idx + raw.length;
  });

  if (cur < text.length) parts.push(text.slice(cur));
  return parts;
}

// ---------------------------------------------------------------------------
// Table helpers
// ---------------------------------------------------------------------------
function isTableRow(line: string): boolean {
  const t = line.trim();
  return t.startsWith("|") && t.endsWith("|");
}

function isSeparatorRow(line: string): boolean {
  return isTableRow(line) && /^\|[\s\-:|]+\|$/.test(line.trim());
}

function parseTableCells(line: string): string[] {
  return line
    .trim()
    .slice(1, -1)
    .split("|")
    .map((c) => c.trim());
}

function renderTable(rows: string[], key: string): React.ReactElement {
  let sepIdx = rows.findIndex((r) => isSeparatorRow(r));
  if (sepIdx === -1) sepIdx = 1;

  const headerRows = rows.slice(0, sepIdx);
  const bodyRows = rows.slice(sepIdx + 1);

  return (
    <div key={key} className="overflow-x-auto my-5 rounded-lg border border-zinc-800 bg-[#18181b]">
      <table className="min-w-full text-sm">
        <thead className="bg-[#141416]">
          {headerRows.map((row, ri) => (
            <tr key={ri}>
              {parseTableCells(row).map((cell, ci) => (
                <th
                  key={ci}
                  className="px-4 py-2.5 text-left font-semibold text-zinc-100 border-b border-zinc-800 whitespace-nowrap"
                >
                  {renderInline(cell)}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {bodyRows.map((row, ri) => (
            <tr
              key={ri}
              className={
                ri % 2 === 0
                  ? "bg-[#18181b] hover:bg-zinc-800/40 transition-colors"
                  : "bg-[#121214] hover:bg-zinc-800/40 transition-colors"
              }
            >
              {parseTableCells(row).map((cell, ci) => (
                <td
                  key={ci}
                  className="px-4 py-2 text-zinc-300 border-b border-zinc-800/60"
                >
                  {renderInline(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single-line renderer
// ---------------------------------------------------------------------------
function renderLine(line: string, index: number): React.ReactNode {
  const trimmed = line.trim();

  if (trimmed.startsWith("#### "))
    return (
      <h4 key={index} className="text-base font-semibold text-zinc-200 mt-4 mb-1.5">
        {renderInline(trimmed.slice(5))}
      </h4>
    );
  if (trimmed.startsWith("### "))
    return (
      <h3 key={index} className="text-lg font-medium text-zinc-200 mt-5 mb-2">
        {renderInline(trimmed.slice(4))}
      </h3>
    );
  if (trimmed.startsWith("## "))
    return (
      <h2 key={index} className="text-xl font-semibold text-white mt-6 mb-2.5 border-b border-zinc-800 pb-1">
        {renderInline(trimmed.slice(3))}
      </h2>
    );
  if (trimmed.startsWith("# "))
    return (
      <h1 key={index} className="text-2xl font-bold text-white mt-6 mb-3 tracking-tight">
        {renderInline(trimmed.slice(2))}
      </h1>
    );

  if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed))
    return <hr key={index} className="border-zinc-800 my-5" />;

  if (trimmed.startsWith("> ")) {
    const quoteText = trimmed.slice(2).trim();
    if (quoteText.startsWith("[!NOTE]"))
      return (
        <div key={index} className="my-4 p-4 rounded-lg bg-[#da7756]/10 border-l-4 border-[#da7756] text-[#da7756] text-sm">
          <span className="font-semibold block mb-1">NOTE</span>
          {quoteText.replace("[!NOTE]", "").trim()}
        </div>
      );
    if (quoteText.startsWith("[!WARNING]"))
      return (
        <div key={index} className="my-4 p-4 rounded-lg bg-amber-500/10 border-l-4 border-amber-500 text-amber-300 text-sm">
          <span className="font-semibold block mb-1">WARNING</span>
          {quoteText.replace("[!WARNING]", "").trim()}
        </div>
      );
    if (quoteText.startsWith("[!IMPORTANT]"))
      return (
        <div key={index} className="my-4 p-4 rounded-lg bg-emerald-500/10 border-l-4 border-emerald-500 text-emerald-300 text-sm">
          <span className="font-semibold block mb-1">IMPORTANT</span>
          {quoteText.replace("[!IMPORTANT]", "").trim()}
        </div>
      );
    if (quoteText.startsWith("[!CAUTION]"))
      return (
        <div key={index} className="my-4 p-4 rounded-lg bg-rose-500/10 border-l-4 border-rose-500 text-rose-300 text-sm">
          <span className="font-semibold block mb-1">CAUTION</span>
          {quoteText.replace("[!CAUTION]", "").trim()}
        </div>
      );
    return (
      <blockquote key={index} className="border-l-4 border-zinc-700 pl-4 py-1 my-3 text-zinc-400 italic bg-zinc-900/30 rounded-r-md">
        {renderInline(quoteText)}
      </blockquote>
    );
  }

  if (trimmed.startsWith("- ") || trimmed.startsWith("* "))
    return (
      <li key={index} className="ml-5 list-disc text-zinc-300 my-1 font-normal">
        {renderInline(trimmed.slice(2))}
      </li>
    );

  const numMatch = trimmed.match(/^(\d+)\.\s(.*)/);
  if (numMatch)
    return (
      <li key={index} className="ml-5 list-decimal text-zinc-300 my-1 font-normal">
        {renderInline(numMatch[2])}
      </li>
    );

  if (trimmed === "") return <div key={index} className="h-2" />;

  return (
    <p key={index} className="text-zinc-300 leading-relaxed my-2 text-sm">
      {renderInline(line)}
    </p>
  );
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content) return <span className="text-zinc-500 italic">No content generated.</span>;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];

  let inCodeBlock = false;
  let codeContent: string[] = [];
  let codeLang = "text";
  let tableBuffer: string[] = [];

  const flushTable = (idx: number) => {
    if (tableBuffer.length > 0) {
      elements.push(renderTable(tableBuffer, `table-${idx}`));
      tableBuffer = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code fence
    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${i}`} className="bg-[#121214] border border-zinc-800 p-4 rounded-lg my-4 font-mono text-xs text-zinc-300 overflow-x-auto">
            <div className="flex justify-between items-center text-[10px] text-zinc-500 border-b border-zinc-800/80 pb-2 mb-3 uppercase tracking-wider">
              <span>{codeLang} Code Block</span>
              <span className="lowercase text-[9px]">read-only</span>
            </div>
            <code>{codeContent.join("\n")}</code>
          </pre>
        );
        codeContent = [];
        inCodeBlock = false;
      } else {
        flushTable(i);
        inCodeBlock = true;
        codeLang = line.trim().slice(3).trim() || "text";
      }
      continue;
    }

    if (inCodeBlock) {
      codeContent.push(line);
      continue;
    }

    // Table rows – buffer them
    if (isTableRow(line)) {
      tableBuffer.push(line);
      continue;
    }

    // Non-table line: flush any accumulated table first
    flushTable(i);
    elements.push(renderLine(line, i));
  }

  // Flush any trailing table
  flushTable(lines.length);

  return <div className="space-y-0.5">{elements}</div>;
}
