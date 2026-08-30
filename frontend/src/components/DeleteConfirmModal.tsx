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
        className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity duration-200"
        onClick={() => {
          if (!isLoading) onClose();
        }}
      />

      {/* Modal Container */}
      <div className="relative w-full max-w-md bg-[#18181b] border border-zinc-800 rounded-2xl p-6 shadow-2xl z-10 transition-all duration-200">
        {/* Close icon */}
        <button
          onClick={onClose}
          disabled={isLoading}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/60 transition disabled:opacity-40 cursor-pointer"
          aria-label="Close dialog"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Content Header */}
        <div className="flex items-start gap-4">
          <div className="w-11 h-11 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center shrink-0">
            <Trash2 className="w-5 h-5" />
          </div>
          <div className="space-y-1 pt-0.5">
            <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              <span>{title}</span>
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed font-normal">
              {description}
            </p>
          </div>
        </div>

        {/* Item preview badge if provided */}
        {(itemLabel || itemSubLabel) && (
          <div className="my-4 p-3.5 rounded-xl bg-[#121214] border border-zinc-800 space-y-1">
            <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider block">
              Target for Deletion
            </span>
            {itemLabel && (
              <p className="text-xs font-semibold text-zinc-200 line-clamp-2 select-text font-mono">
                {itemLabel}
              </p>
            )}
            {itemSubLabel && (
              <p className="text-[11px] text-zinc-400 truncate font-mono">
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
          <div className="mb-4 p-3 rounded-xl bg-rose-950/80 border border-rose-800/50 text-rose-300 text-xs select-text">
            <strong>Error: </strong> {errorMessage}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-white text-xs font-semibold transition disabled:opacity-50 cursor-pointer"
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={() => onConfirm()}
            disabled={isLoading}
            className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-2 transition disabled:opacity-60 cursor-pointer"
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
