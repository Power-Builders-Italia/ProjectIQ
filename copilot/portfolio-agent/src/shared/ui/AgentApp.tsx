// Routes a tool call to its view.
import * as React from 'react';

import type { IntentKey } from '../intents';
import { CreateProjectView } from './views/CreateProjectView';
import { ExploreView } from './views/ExploreView';
import { MyWorkView } from './views/MyWorkView';
import { ProjectDocumentsView } from './views/ProjectDocumentsView';
import { PortfolioHealthView } from './views/PortfolioHealthView';
import { ProjectBudgetView } from './views/ProjectBudgetView';
import { ProjectHealthView } from './views/ProjectHealthView';
import { ProjectTimelineView } from './views/ProjectTimelineView';
import { PurchasingView } from './views/PurchasingView';
import { ResourceLoadView } from './views/ResourceLoadView';
import { SubmitTimesheetView } from './views/SubmitTimesheetView';
import { SupplierComplianceView } from './views/SupplierComplianceView';
import { TimeApprovalsView } from './views/TimeApprovalsView';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Props = Record<string, any>;

export const AgentApp: React.FC<{ intent: IntentKey; properties: Props }> = ({ intent, properties: p }) => {
  switch (intent) {
    case 'GetMyWorkSummary': return <MyWorkView />;
    case 'SubmitTimesheet': return <SubmitTimesheetView project={p.project} hours={p.hours} date={p.date} wbsNode={p.wbsNode} notes={p.notes} weekOf={p.weekOf} />;
    case 'GetProjectHealth': return <ProjectHealthView project={p.project} />;
    case 'GetProjectBudget': return <ProjectBudgetView project={p.project} />;
    case 'GetProjectTimeline': return <ProjectTimelineView project={p.project} />;
    case 'GetProjectDocuments': return <ProjectDocumentsView project={p.project} />;
    case 'CreateProjectFromDocument': return (
      <CreateProjectView documentName={p.documentName} name={p.name} customer={p.customer} projectManager={p.projectManager} startDate={p.startDate}
        endDate={p.endDate} contractValue={p.contractValue} description={p.description} wbs={p.wbs} />
    );
    case 'GetPortfolioHealth': return <PortfolioHealthView health={p.health} customer={p.customer} manager={p.manager} includeClosed={p.includeClosed} />;
    case 'GetResourceLoad': return <ResourceLoadView resource={p.resource} from={p.from} weeks={p.weeks} />;
    case 'GetPurchasingStatus': return <PurchasingView project={p.project} focus={p.focus} />;
    case 'GetSupplierCompliance': return <SupplierComplianceView supplier={p.supplier} />;
    case 'ReviewTimeApprovals': return <TimeApprovalsView project={p.project} resource={p.resource} />;
    default: return <ExploreView />;
  }
};
