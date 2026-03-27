"use client";

import { useState, useEffect } from "react";
import { syllabuses as syllabusApi } from "@/lib/api";
import type { KnowledgeGraphData } from "@/lib/types";

export function useTopicGraph(syllabusId: string | null) {
  const [graph, setGraph] = useState<KnowledgeGraphData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!syllabusId) return;
    let cancelled = false;

    setIsLoading(true);
    setError(null);

    syllabusApi
      .getGraph(syllabusId)
      .then((data) => {
        if (!cancelled) setGraph(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [syllabusId]);

  const refresh = () => {
    if (!syllabusId) return;
    setIsLoading(true);
    syllabusApi
      .getGraph(syllabusId)
      .then(setGraph)
      .catch((err: Error) => setError(err.message))
      .finally(() => setIsLoading(false));
  };

  return { graph, isLoading, error, refresh };
}
