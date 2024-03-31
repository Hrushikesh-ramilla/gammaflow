"use client";

import { useCallback, useEffect } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Edge,
  MiniMap,
  Node,
  NodeChange,
  addEdge,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { TopicNode } from "./TopicNode";

const nodeTypes = { topicNode: TopicNode };

interface KnowledgeGraphProps {
  nodes: Node[];
  edges: Edge[];
  onTopicClick: (topicId: string, topicName: string) => void;
  activeTopicId?: string;
  completedTopicIds: string[];
}

export function KnowledgeGraph({
  nodes: initialNodes,
  edges: initialEdges,
  onTopicClick,
  activeTopicId,
  completedTopicIds,
}: KnowledgeGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update node data when active topic or completed topics change
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        data: {
          ...node.data,
          isActive: node.id === activeTopicId,
          isCompleted: completedTopicIds.includes(node.id),
          onClick: () => onTopicClick(node.id, node.data.label),
        },
        selected: node.id === activeTopicId,
      }))
    );
  }, [activeTopicId, completedTopicIds, onTopicClick, setNodes]);

  return (
    <div className="w-full h-full" style={{ background: "rgb(3 7 18)" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
        attributionPosition="bottom-right"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="rgb(55 65 81)"
        />
        <Controls />
        <MiniMap
          style={{ background: "rgb(17 24 39)", border: "1px solid rgb(55 65 81)" }}
          nodeColor={(node) => {
            if (node.data?.isCompleted) return "rgb(34 197 94)";
            if (node.data?.isActive) return "rgb(99 102 241)";
            return "rgb(55 65 81)";
          }}
        />
      </ReactFlow>
    </div>
  );
}
