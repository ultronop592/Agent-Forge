"use client";

import { useState, useEffect } from "react";
import { 
  Compass, 
  Send, 
  CheckCircle, 
  XCircle, 
  ShieldAlert,
  Clock
} from "lucide-react";

interface SteeringPanelProps {
  confidenceScore: number | null;
  verifierFeedback: string;
  onSteer: (steeringPrompt: string) => Promise<void>;
  onForceComplete: () => Promise<void>;
  onCancel: () => Promise<void>;
}

export default function SteeringPanel({
  confidenceScore,
  verifierFeedback,
  onSteer,
  onForceComplete,
  onCancel,
}: SteeringPanelProps) {
  const [steeringText, setSteeringText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(60);

  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleSteerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!steeringText.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSteer(steeringText);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForceCompleteClick = async () => {
    setIsSubmitting(true);
    try {
      await onForceComplete();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelClick = async () => {
    setIsSubmitting(true);
    try {
      await onCancel();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-panel-elevated rounded-2xl p-6 space-y-5 border border-[#da7756]/30 bg-[#1e1e24] relative overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-[#da7756]/20 text-[#da7756] flex items-center justify-center">
            <Compass className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Human-in-the-Loop: Dynamic Steering Gate</span>
              <span className="w-2 h-2 rounded-full bg-[#da7756]" />
            </h3>
            <p className="text-xs text-zinc-400">
              The Verifier flagged an item. Steer the workforce with feedback or accept the result.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-[#141416] border border-zinc-800 px-3 py-1.5 rounded-xl shrink-0">
          <Clock className="w-3.5 h-3.5 text-[#da7756]" />
          <span className="text-[11px] font-semibold text-zinc-300">
            Auto-retry in: <strong className="text-[#da7756] font-mono">{secondsLeft}s</strong>
          </span>
        </div>
      </div>

      {/* Verifier Feedback Quote Box */}
      <div className="p-4 rounded-xl bg-[#da7756]/10 border border-[#da7756]/20 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[#da7756] text-xs font-bold uppercase tracking-wider">
            <ShieldAlert className="w-4 h-4" />
            <span>Verifier Inspection Notice</span>
          </div>
          {confidenceScore !== null && (
            <span className="text-[10px] font-bold text-[#da7756] bg-[#da7756]/20 border border-[#da7756]/30 px-2 py-0.5 rounded-full">
              Confidence: {Math.round(confidenceScore * 100)}%
            </span>
          )}
        </div>
        <p className="text-xs text-zinc-200 leading-relaxed font-medium select-text">
          {verifierFeedback}
        </p>
      </div>

      {/* Steering Input Form */}
      <form onSubmit={handleSteerSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider block">
            Steering Instructions / Feedback
          </label>
          <textarea
            rows={3}
            value={steeringText}
            onChange={(e) => setSteeringText(e.target.value)}
            placeholder="Tell the Execution & Reasoning agents what to fix (e.g. 'Use Python 3.12 syntax', 'Provide exact compensation numbers', 'Add more error handling')..."
            className="w-full bg-[#121214] border border-zinc-800 rounded-xl p-3.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 transition resize-none leading-relaxed"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <button
            type="button"
            onClick={handleCancelClick}
            disabled={isSubmitting}
            className="px-4 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition w-full sm:w-auto justify-center cursor-pointer"
          >
            <XCircle className="w-4 h-4 text-rose-400" />
            <span>Cancel Task</span>
          </button>

          <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
            <button
              type="button"
              onClick={handleForceCompleteClick}
              disabled={isSubmitting}
              className="px-4 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
            >
              <CheckCircle className="w-4 h-4 text-emerald-400" />
              <span>Accept As-Is</span>
            </button>
            <button
              type="submit"
              disabled={!steeringText.trim() || isSubmitting}
              className="px-5 py-2.5 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white text-xs font-bold flex items-center gap-2 transition-colors disabled:opacity-40 cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Submit Steering Feedback</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
