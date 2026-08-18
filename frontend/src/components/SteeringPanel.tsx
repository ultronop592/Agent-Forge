"use client";

import { useState, useEffect } from "react";
import { 
  Compass, 
  Send, 
  CheckCircle, 
  XCircle, 
  ShieldAlert,
  Sparkles,
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
    <div className="glass-panel-elevated rounded-2xl p-6 space-y-5 border border-amber-500/30 shadow-2xl relative overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center">
            <Compass className="w-4 h-4 animate-spin" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Human-in-the-Loop: Dynamic Steering Gate</span>
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            </h3>
            <p className="text-xs text-slate-400">
              The Verifier flagged an item. Steer the workforce with feedback or accept the result.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-xl shrink-0">
          <Clock className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
          <span className="text-[11px] font-semibold text-slate-300">
            Auto-retry in: <strong className="text-amber-400 font-mono">{secondsLeft}s</strong>
          </span>
        </div>
      </div>

      {/* Verifier Feedback Quote Box */}
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-amber-400 text-xs font-bold uppercase tracking-wider">
            <ShieldAlert className="w-4 h-4" />
            <span>Verifier Inspection Notice</span>
          </div>
          {confidenceScore !== null && (
            <span className="text-[10px] font-bold text-amber-300 bg-amber-500/20 border border-amber-500/30 px-2 py-0.5 rounded-full">
              Confidence: {Math.round(confidenceScore * 100)}%
            </span>
          )}
        </div>
        <p className="text-xs text-slate-200 leading-relaxed font-medium select-text">
          {verifierFeedback}
        </p>
      </div>

      {/* Steering Input Form */}
      <form onSubmit={handleSteerSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
            Steering Instructions / Feedback
          </label>
          <textarea
            rows={3}
            value={steeringText}
            onChange={(e) => setSteeringText(e.target.value)}
            placeholder="Tell the Execution & Reasoning agents what to fix (e.g. 'Use Python 3.12 syntax', 'Provide exact compensation numbers', 'Add more error handling')..."
            className="w-full bg-[#080b12] border border-slate-800 rounded-xl p-3.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500/60 transition resize-none leading-relaxed"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <button
            type="button"
            onClick={handleCancelClick}
            disabled={isSubmitting}
            className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition w-full sm:w-auto justify-center cursor-pointer"
          >
            <XCircle className="w-4 h-4 text-rose-400" />
            <span>Cancel Task</span>
          </button>

          <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
            <button
              type="button"
              onClick={handleForceCompleteClick}
              disabled={isSubmitting}
              className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
            >
              <CheckCircle className="w-4 h-4 text-emerald-400" />
              <span>Accept As-Is</span>
            </button>
            <button
              type="submit"
              disabled={!steeringText.trim() || isSubmitting}
              className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold flex items-center gap-2 transition-colors disabled:opacity-40 cursor-pointer"
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
