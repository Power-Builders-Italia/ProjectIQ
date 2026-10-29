import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IGetProjectBudgetProperties } from './GetProjectBudgetCopilotComponentProperties';

export default class GetProjectBudgetCopilotComponent extends ProjectIQCopilotComponentBase<IGetProjectBudgetProperties> {
  protected intentKey = 'GetProjectBudget' as const;
}
