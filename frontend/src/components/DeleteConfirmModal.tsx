"use client";

import React, { useEffect } from "react";
import { AlertTriangle, Trash2, X, Loader2 } from "lucide-react";

export interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void> | void;
  title?: string;
  description?: string;
  itemLabel?: string;
  itemSubLabel?: string;
  confirmText?: string;
  cancelText?: string;
  isLoading?: boolean;
  errorMessage?: string | null;
}

export default function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title = "Delete Item",
  description = "Are you sure you want to delete this item? This action is permanent and cannot be undone.",
  itemLabel,
  itemSubLabel,
  confirmText = "Delete Permanently",
  cancelText = "Cancel",
  isLoading = false,
  errorMessage = null,
}: DeleteConfirmModalProps) {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isLoading) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isLoading, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-md transition-opacity duration-300 animate-in fade-in"
        onClick={() => {
          if (!isLoading) onClose();
        }}
      />

      {/* Modal Container */}
      <div className="relative w-full max-w-md bg-gradient-to-b from-slate-900 via-slate-950 to-slate-950 border border-slate-800/90 rounded-2xl p-6 shadow-2xl shadow-rose-950/20 z-10 transition-all duration-300 animate-in zoom-in-95 scale-100">
        {/* Glow ambient highlight */}
        <div className="absolute top-0 right-1/2 translate-x-1/2 -translate-y-1/2 w-48 h-20 bg-rose-600/15 rounded-full blur-2xl pointer-events-none" />

        {/* Close icon */}
        <button
          onClick={onClose}
          disabled={isLoading}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 transition disabled:opacity-40"
          aria-label="Close dialog"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Content Header */}
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center shrink-0 shadow-inner">
            <Trash2 className="w-6 h-6 animate-pulse" />
          </div>
          <div className="space-y-1 pt-0.5">
            <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <span>{title}</span>
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed font-normal">
              {description}
            </p>
          </div>
        </div>

        {/* Item preview badge if provided */}
        {(itemLabel || itemSubLabel) && (
          <div className="my-4 p-3.5 rounded-xl bg-slate-900/90 border border-slate-800/80 space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block">
              Target for Deletion
            </span>
            {itemLabel && (
              <p className="text-xs font-semibold text-slate-200 line-clamp-2 select-text font-mono">
                {itemLabel}
              </p>
            )}
            {itemSubLabel && (
              <p className="text-[11px] text-slate-400 truncate font-mono">
                {itemSubLabel}
              </p>
            )}
          </div>
        )}

        {/* Warning alert notice */}
        <div className="my-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span className="leading-tight font-medium text-[11px]">
            All associated subtasks, logs, and agent artifacts will be erased immediately.
          </span>
        </div>

        {/* Error message display if any */}
        {errorMessage && (
          <div className="mb-4 p-3 rounded-xl bg-red-950/80 border border-red-700/50 text-red-300 text-xs select-text">
            <strong>Error: </strong> {errorMessage}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold transition disabled:opacity-50 cursor-pointer"
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={() => onConfirm()}
            disabled={isLoading}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white text-xs font-semibold shadow-lg shadow-rose-950/50 flex items-center gap-2 transition disabled:opacity-60 cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                <span>{confirmText}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
