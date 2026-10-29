import * as React from 'react';

import type { ProjectIQService } from '../services/ProjectIQService';
import type { AgentSettings } from '../settings';

export interface IAgentContext {
  /** Resolves once settings are read and the Dataverse client is ready. */
  ready: Promise<{ service: ProjectIQService; settings: AgentSettings }>;
  /** Today as a day number in the user's time zone. */
  today: number;
  /** True in full screen or when the inline container is wide enough for extra columns. */
  wide: boolean;
  fullscreen: boolean;
  onRequestFullscreen?: () => void;
  /** Opens a link through the Copilot host (new tab). */
  openLink: (url: string) => void;
  /** Sends a prompt to Copilot as if the user typed it, to open another view. */
  followUp: (prompt: string) => void;
  /** Tells Copilot what the view shows, so follow-up questions use it (at most 10 KB). */
  setModelContext: (text: string) => void;
}

export const AgentContext = React.createContext<IAgentContext | undefined>(undefined);

export function useAgent(): IAgentContext {
  const ctx = React.useContext(AgentContext);
  if (!ctx) throw new Error('AgentContext missing');
  return ctx;
}

export interface AsyncState<T> {
  data?: T;
  error?: Error;
  loading: boolean;
  reload: () => void;
}

/** Runs `load` with the service once ready, again when `deps` change or on reload. */
export function useServiceData<T>(load: (service: ProjectIQService, settings: AgentSettings) => Promise<T>, deps: React.DependencyList): AsyncState<T> {
  const { ready } = useAgent();
  const [state, setState] = React.useState<{ data?: T; error?: Error; loading: boolean }>({ loading: true });
  const [tick, setTick] = React.useState(0);
  React.useEffect(() => {
    let alive = true;
    setState(s => ({ data: s.data, loading: true }));
    ready.then(({ service, settings }) => load(service, settings))
      .then(data => { if (alive) setState({ data, loading: false }); })
      .catch((error: Error) => { if (alive) setState({ error, loading: false }); });
    return () => { alive = false; };
  }, [ready, tick, ...deps]);
  const reload = React.useCallback(() => setTick(t => t + 1), []);
  return { ...state, reload };
}
