"use client";

import { useState } from "react";
import { 
  Compass, 
  Send, 
  CheckCircle, 
  XCircle, 
  ShieldAlert,
  Sparkles
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

  const scorePct = confidenceScore !== null ? Math.round(confidenceScore * 100) : 70;

  return (
    <div className="glass-panel border-2 border-blue-500/40 rounded-2xl p-6 shadow-2xl relative overflow-hidden bg-slate-950/85 mb-8 animate-fade-in">
      <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-850 pb-4 mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Compass className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="bg-blue-500/20 text-blue-400 border border-blue-500/40 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">
                Human Steering Intercept
              </span>
              <span className="bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded text-[10px] font-bold">
                🎯 {scorePct}% QA Confidence
              </span>
            </div>
            <h3 className="text-lg font-bold text-white mt-1">Provide Dynamic Steering Guidance</h3>
          </div>
        </div>
        <p className="text-xs text-slate-400 max-w-sm font-medium">
          The Verifier flagged areas for improvement. Inject explicit guidance to steer the Executor or accept the current output.
        </p>
      </div>

      {/* Verifier Feedback Callout Box */}
      {verifierFeedback && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 mb-5">
          <div className="flex items-center gap-2 text-amber-400 font-bold text-xs mb-1.5">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <span>Verifier Agent Findings & Revision Hint</span>
          </div>
          <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
            {verifierFeedback}
          </p>
        </div>
      )}

      {/* Steering Input Form */}
      <form onSubmit={handleSteerSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span>Your Custom Steering Instructions</span>
          </label>
          <textarea
            value={steeringText}
            onChange={(e) => setSteeringText(e.target.value)}
            rows={3}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-xs text-slate-200 font-medium placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition-colors"
            placeholder="e.g. 'Refocus section 2 on developer API pricing tiers, and add a comparative chart snippet for open-source alternatives...'"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <button
            type="button"
            onClick={handleCancelClick}
            disabled={isSubmitting}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-bold transition-all disabled:opacity-50 w-full sm:w-auto justify-center"
          >
            <XCircle className="w-4 h-4" />
            <span>Cancel Task</span>
          </button>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            <button
              type="button"
              onClick={handleForceCompleteClick}
              disabled={isSubmitting}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 text-xs font-bold transition-all disabled:opacity-50"
            >
              <CheckCircle className="w-4 h-4" />
              <span>Accept Current Draft & Complete</span>
            </button>

            <button
              type="submit"
              disabled={!steeringText.trim() || isSubmitting}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-extrabold shadow-lg shadow-blue-900/30 transition-all hover:scale-[1.02] disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>Submit Steering & Re-run</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
