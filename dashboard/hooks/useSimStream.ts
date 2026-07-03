"use client";

import { useEffect, useRef, useState } from "react";
import { simStreamUrl } from "@/lib/api";
import type { TickResultPayload } from "@/lib/types";

interface SimStreamState {
  history: TickResultPayload[];
  latest: TickResultPayload | null;
  finished: boolean;
  error: string | null;
}

const EMPTY_STATE: SimStreamState = { history: [], latest: null, finished: false, error: null };

/**
 * Subscribes to `/sim/stream` for `simId` and accumulates each tick's
 * payload (deliberation result + world-state snapshot). Reconnects from
 * scratch whenever `simId` changes; closes the connection on unmount or
 * once the server sends its "done" event.
 */
export function useSimStream(simId: string | null, intervalMs = 300): SimStreamState {
  const [state, setState] = useState<SimStreamState>(EMPTY_STATE);
  const sourceRef = useRef<EventSource | null>(null);

  // Reset local state as soon as `simId` changes, during render rather than
  // in an effect -- React's documented pattern for "state that depends on a
  // prop" (https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes).
  const [trackedSimId, setTrackedSimId] = useState(simId);
  if (trackedSimId !== simId) {
    setTrackedSimId(simId);
    setState(EMPTY_STATE);
  }

  useEffect(() => {
    sourceRef.current?.close();
    if (!simId) return;

    const source = new EventSource(simStreamUrl(simId, intervalMs));
    sourceRef.current = source;

    source.addEventListener("tick", (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data) as TickResultPayload;
      setState((prev) => ({
        ...prev,
        history: [...prev.history, payload],
        latest: payload,
      }));
    });

    source.addEventListener("done", () => {
      setState((prev) => ({ ...prev, finished: true }));
      source.close();
    });

    source.onerror = () => {
      setState((prev) => ({ ...prev, error: "Stream connection lost" }));
      source.close();
    };

    return () => source.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [simId]);

  return state;
}
