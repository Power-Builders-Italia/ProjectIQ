import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IGetProjectHealthProperties } from './GetProjectHealthCopilotComponentProperties';

export default class GetProjectHealthCopilotComponent extends ProjectIQCopilotComponentBase<IGetProjectHealthProperties> {
  protected intentKey = 'GetProjectHealth' as const;
}
