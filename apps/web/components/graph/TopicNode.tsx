"use client";

import { Handle, NodeProps, Position } from "reactflow";
import { CheckCircle2, Circle, PlayCircle } from "lucide-react";
import { motion } from "framer-motion";

interface TopicNodeData {
  label: string;
  description: string;
  depth: "introductory" | "intermediate" | "advanced";
  isActive?: boolean;
  isCompleted?: boolean;
  status?: string;
  onClick?: () => void;
}

const DEPTH_COLORS = {
  introductory: "from-emerald-500/20 to-teal-500/20 border-emerald-500/40",
  intermediate: "from-indigo-500/20 to-violet-500/20 border-indigo-500/40",
  advanced: "from-rose-500/20 to-pink-500/20 border-rose-500/40",
};

export function TopicNode({ data, id }: NodeProps<TopicNodeData>) {
  const isActive = data.isActive;
  const isCompleted = data.isCompleted;
  const depthClass = DEPTH_COLORS[data.depth] || DEPTH_COLORS.intermediate;

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-indigo-500 !border-indigo-400" />

      <motion.div
        onClick={data.onClick}
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.98 }}
        className={`
          relative w-52 px-4 py-3 rounded-2xl cursor-pointer border bg-gradient-to-br
          ${depthClass}
          ${isActive ? "ring-2 ring-indigo-500 shadow-lg shadow-indigo-500/30 scale-105" : ""}
          ${isCompleted ? "opacity-70" : ""}
          transition-all duration-150
        `}
      >
        {/* Status icon */}
        <div className="absolute top-3 right-3">
          {isCompleted ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : isActive ? (
            <PlayCircle className="w-4 h-4 text-indigo-400 animate-pulse" />
          ) : (
            <Circle className="w-4 h-4 text-gray-600" />
          )}
        </div>

        {/* Topic name */}
        <p className="font-semibold text-sm text-white pr-5 leading-snug mb-1">
          {data.label}
        </p>

        {/* Description */}
        {data.description && (
          <p className="text-xs text-gray-400 leading-snug line-clamp-2">
            {data.description}
          </p>
        )}

        {/* Depth badge */}
        <div className="mt-2">
          <span className="text-[10px] uppercase tracking-widest text-gray-500">
            {data.depth}
          </span>
        </div>
      </motion.div>

      <Handle type="source" position={Position.Bottom} className="!bg-indigo-500 !border-indigo-400" />
    </>
  );
}
