"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { KnowledgeGraph } from "@/components/graph/KnowledgeGraph";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { PDFViewer } from "@/components/pdf/PDFViewer";
import { Brain, PanelLeft, PanelRight, Maximize2 } from "lucide-react";

interface Citation {
  pageNumber: number;
  documentName: string;
  charStart?: number;
  charEnd?: number;
  sourceType?: "PDF" | "OCR";
}

// Mock data — replace with real API data
const MOCK_NODES = [
  { id: "arrays", type: "topicNode", position: { x: 0, y: 0 }, data: { label: "Arrays", description: "Fundamental data structure", depth: "introductory", status: "completed" } },
  { id: "linked-lists", type: "topicNode", position: { x: 280, y: 0 }, data: { label: "Linked Lists", description: "Pointer-based linear structure", depth: "introductory", status: "completed", prerequisites: ["arrays"] } },
  { id: "stacks-queues", type: "topicNode", position: { x: 140, y: 180 }, data: { label: "Stacks & Queues", description: "LIFO and FIFO abstractions", depth: "intermediate", prerequisites: ["arrays", "linked-lists"] } },
  { id: "trees", type: "topicNode", position: { x: 0, y: 360 }, data: { label: "Trees", description: "Hierarchical data structures", depth: "intermediate", prerequisites: ["linked-lists"] } },
  { id: "graphs", type: "topicNode", position: { x: 280, y: 360 }, data: { label: "Graphs", description: "Nodes and edges relationship model", depth: "advanced", prerequisites: ["trees"] } },
  { id: "sorting", type: "topicNode", position: { x: 560, y: 180 }, data: { label: "Sorting Algorithms", description: "Comparison and non-comparison sorts", depth: "intermediate", prerequisites: ["arrays"] } },
  { id: "dp", type: "topicNode", position: { x: 420, y: 360 }, data: { label: "Dynamic Programming", description: "Optimal substructure and memoization", depth: "advanced", prerequisites: ["sorting"] } },
];

const MOCK_EDGES = [
  { id: "e1", source: "arrays", target: "linked-lists", type: "topicEdge" },
  { id: "e2", source: "arrays", target: "stacks-queues", type: "topicEdge" },
  { id: "e3", source: "linked-lists", target: "stacks-queues", type: "topicEdge" },
  { id: "e4", source: "linked-lists", target: "trees", type: "topicEdge" },
  { id: "e5", source: "trees", target: "graphs", type: "topicEdge" },
  { id: "e6", source: "arrays", target: "sorting", type: "topicEdge" },
  { id: "e7", source: "sorting", target: "dp", type: "topicEdge" },
];

type Panel = "graph" | "chat" | "pdf";

export default function StudyPage({ params }: { params: { id: string } }) {
  const [activeTopicId, setActiveTopicId] = useState("stacks-queues");
  const [activeTopicName, setActiveTopicName] = useState("Stacks & Queues");
  const [targetPage, setTargetPage] = useState(1);
  const [lastCitation, setLastCitation] = useState<Citation | null>(null);
  const [deviationDepth, setDeviationDepth] = useState(0);
  const [hiddenPanels, setHiddenPanels] = useState<Set<Panel>>(new Set());

  const handleTopicClick = useCallback((topicId: string, topicName: string) => {
    setActiveTopicId(topicId);
    setActiveTopicName(topicName);
  }, []);

  const handleCitationClick = useCallback((citation: Citation) => {
    setLastCitation(citation);
    setTargetPage(citation.pageNumber);
  }, []);

  const handleResume = useCallback(() => {
    setDeviationDepth(0);
  }, []);

  const togglePanel = (panel: Panel) => {
    setHiddenPanels((prev) => {
      const next = new Set(prev);
      if (next.has(panel)) next.delete(panel);
      else next.add(panel);
      return next;
    });
  };

  const visiblePanels = 3 - hiddenPanels.size;
  const panelWidth = `${100 / visiblePanels}%`;

  return (
    <div className="h-screen flex flex-col bg-gray-950 overflow-hidden">
      {/* Top bar */}
      <header className="h-12 glass border-b border-white/5 flex items-center justify-between px-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center">
            <Brain className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-white">SYL</span>
          <div className="h-4 w-px bg-gray-700" />
          <span className="text-sm text-gray-400">Data Structures & Algorithms</span>
        </div>

        {/* Panel toggles */}
        <div className="flex items-center gap-1">
          {(["graph", "chat", "pdf"] as Panel[]).map((panel) => (
            <button
              key={panel}
              onClick={() => togglePanel(panel)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                hiddenPanels.has(panel)
                  ? "text-gray-600 hover:text-gray-400"
                  : "text-indigo-400 bg-indigo-500/10"
              }`}
            >
              {panel.toUpperCase()}
            </button>
          ))}
        </div>
      </header>

      {/* Three-panel layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Knowledge Graph */}
        {!hiddenPanels.has("graph") && (
          <motion.div
            layout
            className="h-full border-r border-white/5 relative"
            style={{ width: panelWidth }}
          >
            <div className="absolute top-3 left-3 z-10">
              <div className="glass rounded-lg px-3 py-1">
                <p className="text-xs text-gray-400">Knowledge Graph</p>
              </div>
            </div>
            <KnowledgeGraph
              nodes={MOCK_NODES as any}
              edges={MOCK_EDGES as any}
              onTopicClick={handleTopicClick}
              activeTopicId={activeTopicId}
              completedTopicIds={["arrays", "linked-lists"]}
            />
          </motion.div>
        )}

        {/* Middle: Chat */}
        {!hiddenPanels.has("chat") && (
          <motion.div
            layout
            className="h-full border-r border-white/5"
            style={{ width: panelWidth }}
          >
            <ChatPanel
              sessionId={params.id}
              topicName={activeTopicName}
              onCitationClick={handleCitationClick}
              deviationDepth={deviationDepth}
              onResume={handleResume}
            />
          </motion.div>
        )}

        {/* Right: PDF Viewer */}
        {!hiddenPanels.has("pdf") && (
          <motion.div
            layout
            className="h-full"
            style={{ width: panelWidth }}
          >
            <PDFViewer
              fileUrl=""
              targetPage={targetPage}
              highlightCharStart={lastCitation?.charStart}
              highlightCharEnd={lastCitation?.charEnd}
              sourceType={lastCitation?.sourceType}
              onPageChange={setTargetPage}
            />
          </motion.div>
        )}
      </div>
    </div>
  );
}
