// Resolves the project written in the prompt; asks the user to choose when it is missing or ambiguous.
import * as React from 'react';

import { useAgent, useServiceData } from '../AgentContext';
import { Choices, ErrorBar, Info, Loading, Shell } from '../kit';
import { matchProjects, PROJECT_STATUS, type ProjectFigures } from '../../logic/portfolio';
import { promptFor, type IntentKey } from '../../intents';

export interface ProjectGateProps {
  intent: IntentKey;
  eyebrow: string;
  title: string;
  project?: string;
  children: (project: ProjectFigures, currencySymbol: string | undefined) => React.ReactElement;
}

export const ProjectGate: React.FC<ProjectGateProps> = props => {
  const { wide } = useAgent();
  const state = useServiceData(s => s.projects(true), []);
  if (state.loading && !state.data) return <Shell eyebrow={props.eyebrow} title={props.title}><Loading /></Shell>;
  if (state.error) return <Shell eyebrow={props.eyebrow} title={props.title}><ErrorBar error={state.error} /></Shell>;
  const all = state.data!.projects;
  const matches = matchProjects(all, props.project);
  if (matches.length === 1) return props.children(matches[0], state.data!.currencySymbol);
  const candidates = (matches.length ? matches : all.filter(p => p.status === PROJECT_STATUS.inProgress)).slice(0, wide ? 24 : 8);
  return (
    <Shell eyebrow={props.eyebrow} title={props.title}>
      <Info title={matches.length ? 'Several projects match' : props.project ? `No project matches "${props.project}"` : 'Which project?'}>
        {candidates.length ? 'Choose the project:' : 'No In Progress project is visible to you.'}
      </Info>
      <Choices items={candidates.map(p => ({
        key: p.id, label: `${p.code} ${p.name}`.trim(), prompt: promptFor(props.intent, p.code || p.name),
      }))} />
    </Shell>
  );
};
