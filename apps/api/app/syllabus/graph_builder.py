"""DAG builder — constructs directed acyclic graph from topic tree."""

from typing import Any


class DAGBuilder:
    """Builds a DAG layout from topic tree for React Flow.

    Performs topological sort + Sugiyama-style (simplified) layer assignment
    so the graph renders cleanly without prerequisite arrows going backwards.
    """

    NODE_WIDTH = 200
    NODE_HEIGHT = 80
    H_GAP = 80
    V_GAP = 120

    def build(self, topics: list[dict]) -> dict[str, Any]:
        """Build nodes and edges for React Flow from topic list.

        Returns:
            dict with 'nodes' and 'edges' arrays (React Flow format)
        """
        # Build prerequisite map
        prereq_map: dict[str, list[str]] = {t["id"]: t.get("prerequisites", []) for t in topics}

        # Topological sort → assigns layer (depth) to each topic
        layers = self._assign_layers(topics, prereq_map)

        # Assign x/y positions based on layer
        nodes = self._build_nodes(topics, layers)
        edges = self._build_edges(topics)

        return {"nodes": nodes, "edges": edges}

    def _assign_layers(self, topics: list[dict], prereq_map: dict) -> dict[str, int]:
        """Assign a layer index to each topic via BFS from roots."""
        layers: dict[str, int] = {}
        in_degree: dict[str, int] = {t["id"]: 0 for t in topics}

        for topic in topics:
            for prereq in prereq_map.get(topic["id"], []):
                if prereq in in_degree:
                    in_degree[topic["id"]] += 1

        # Start with topics that have no prerequisites (roots)
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        for tid in queue:
            layers[tid] = 0

        visited = set(queue)
        while queue:
            current = queue.pop(0)
            for topic in topics:
                if current in topic.get("prerequisites", []) and topic["id"] not in visited:
                    layers[topic["id"]] = layers[current] + 1
                    visited.add(topic["id"])
                    queue.append(topic["id"])

        # Assign any remaining unvisited topics (safety)
        for topic in topics:
            if topic["id"] not in layers:
                layers[topic["id"]] = 0

        return layers

    def _build_nodes(self, topics: list[dict], layers: dict[str, int]) -> list[dict]:
        """Build React Flow node objects with positions."""
        # Group topics by layer
        layer_groups: dict[int, list[str]] = {}
        for topic in topics:
            layer = layers.get(topic["id"], 0)
            layer_groups.setdefault(layer, []).append(topic["id"])

        # Assign positions
        id_to_topic = {t["id"]: t for t in topics}
        nodes = []
        for layer_idx, topic_ids in sorted(layer_groups.items()):
            for col_idx, topic_id in enumerate(topic_ids):
                topic = id_to_topic[topic_id]
                x = col_idx * (self.NODE_WIDTH + self.H_GAP)
                y = layer_idx * (self.NODE_HEIGHT + self.V_GAP)
                nodes.append({
                    "id": topic_id,
                    "type": "topicNode",
                    "position": {"x": x, "y": y},
                    "data": {
                        "label": topic["name"],
                        "description": topic.get("description", ""),
                        "depth": topic.get("estimated_depth", "intermediate"),
                        "status": "not_started",
                        "prerequisites": topic.get("prerequisites", []),
                    },
                })
        return nodes

    def _build_edges(self, topics: list[dict]) -> list[dict]:
        """Build React Flow edge objects from prerequisites."""
        edges = []
        for topic in topics:
            for prereq_id in topic.get("prerequisites", []):
                edge_id = f"e-{prereq_id}-{topic['id']}"
                edges.append({
                    "id": edge_id,
                    "source": prereq_id,
                    "target": topic["id"],
                    "type": "topicEdge",
                    "animated": False,
                    "style": {"stroke": "#6366F1", "strokeWidth": 2},
                    "markerEnd": {"type": "ArrowClosed", "color": "#6366F1"},
                })
        return edges
