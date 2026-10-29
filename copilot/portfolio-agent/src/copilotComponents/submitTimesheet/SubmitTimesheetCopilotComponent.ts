import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { ISubmitTimesheetProperties } from './SubmitTimesheetCopilotComponentProperties';

export default class SubmitTimesheetCopilotComponent extends ProjectIQCopilotComponentBase<ISubmitTimesheetProperties> {
  protected intentKey = 'SubmitTimesheet' as const;
}
