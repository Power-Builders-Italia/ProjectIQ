import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IGetProjectTimelineProperties } from './GetProjectTimelineCopilotComponentProperties';

export default class GetProjectTimelineCopilotComponent extends ProjectIQCopilotComponentBase<IGetProjectTimelineProperties> {
  protected intentKey = 'GetProjectTimeline' as const;
}
