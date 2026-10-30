import * as React from 'react';
import { Link, Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow, Text } from '@fluentui/react-components';
import { Document16Regular, Folder16Regular } from '@fluentui/react-icons';

import { useAgent, useServiceData } from '../AgentContext';
import { ErrorBar, FollowUp, Footer, Info, Kpi, KpiGrid, Loading, OpenInApp, Shell } from '../kit';
import { date } from '../format';
import { ProjectGate } from './ProjectGate';
import { documentSummary, fileSize } from '../../logic/documents';
import type { ProjectFigures } from '../../logic/portfolio';
import { SharePointError } from '../../services/SharePointClient';
import { promptFor } from '../../intents';
import { recordUrl } from '../../settings';
import { culture, strings } from '../../i18n';

const Detail: React.FC<{ project: ProjectFigures }> = ({ project }) => {
  const { wide, fullscreen, openLink, setModelContext } = useAgent();
  const t = strings().documents;
  const state = useServiceData(async (service, settings) => ({ folders: await service.documents(project.id), settings }), [project.id]);
  const summary = React.useMemo(() => (state.data ? documentSummary(state.data.folders) : undefined), [state.data]);
  React.useEffect(() => {
    if (!summary || !state.data) return;
    setModelContext(`Documents of project ${project.code} ${project.name} in SharePoint (${state.data.folders.map(f => f.url).join(', ') || 'no folder'}): `
      + `${summary.files} files, ${summary.folders} folders. `
      + summary.items.map(i => `${i.folder ? 'folder' : 'file'} ${i.name}, modified ${date(i.modified)}${i.modifiedBy ? ' by ' + i.modifiedBy : ''}`).join('; '));
  }, [summary]);
  const access = state.error instanceof SharePointError && (state.error.status === 401 || state.error.status === 403);
  const limit = fullscreen ? 100 : wide ? 25 : 10;
  const folders = state.data?.folders || [];
  return (
    <Shell eyebrow={t.eyebrow} title={`${project.code} ${project.name}`.trim()} subtitle={t.subtitle} onRefresh={state.reload}>
      {access && <Info intent="warning">{t.noAccess}</Info>}
      {state.error && !access && <ErrorBar error={state.error} />}
      {state.loading && !summary && <Loading />}
      {summary && state.data && (
        <>
          {!folders.length && <Info title={t.noLocation}>{t.noLocationHelp}</Info>}
          {folders.some(f => !f.exists) && <Info intent="warning">{t.notCreated}</Info>}
          {folders.length > 0 && (
            <KpiGrid>
              <Kpi label={t.files} value={String(summary.files)} />
              <Kpi label={t.folders} value={String(summary.folders)} />
              <Kpi label={t.lastChange} value={date(summary.lastModified)} note={summary.lastModifiedBy ? t.by(summary.lastModifiedBy) : undefined} />
            </KpiGrid>
          )}
          {folders.some(f => f.exists) && !summary.items.length && <Text>{t.empty}</Text>}
          {summary.items.length > 0 && (
            <Table size="small" aria-label={t.table}>
              <TableHeader>
                <TableRow>
                  <TableHeaderCell>{t.name}</TableHeaderCell>
                  <TableHeaderCell>{t.modified}</TableHeaderCell>
                  {wide && <TableHeaderCell>{t.modifiedBy}</TableHeaderCell>}
                  {wide && <TableHeaderCell>{t.size}</TableHeaderCell>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.items.slice(0, limit).map(i => (
                  <TableRow key={i.url}>
                    <TableCell>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                        {i.folder ? <Folder16Regular /> : <Document16Regular />}
                        <Link onClick={() => openLink(i.url)}>{i.name}</Link>
                      </span>
                    </TableCell>
                    <TableCell>{date(i.modified)}</TableCell>
                    {wide && <TableCell>{i.modifiedBy || '–'}</TableCell>}
                    {wide && <TableCell>{i.folder ? t.items(i.size) : fileSize(i.size, culture())}</TableCell>}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {summary.items.length > limit && <Text size={200}>{t.more(summary.items.length - limit)}</Text>}
          <Text size={200}>{t.note}</Text>
          <Footer>
            {folders.filter(f => f.exists).map(f => <OpenInApp key={f.url} url={f.url} label={t.openFolder} />)}
            <OpenInApp url={recordUrl(state.data.settings, 'op365_project', project.id)} />
            <FollowUp prompt={promptFor('GetProjectHealth', project.code || project.name)}>{t.health}</FollowUp>
          </Footer>
        </>
      )}
    </Shell>
  );
};

export const ProjectDocumentsView: React.FC<{ project?: string }> = props => (
  <ProjectGate intent="GetProjectDocuments" eyebrow={strings().documents.eyebrow} title={strings().intents.GetProjectDocuments.title} project={props.project}>
    {project => <Detail project={project} />}
  </ProjectGate>
);
