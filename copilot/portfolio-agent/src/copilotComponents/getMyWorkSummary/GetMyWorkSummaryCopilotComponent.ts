import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IGetMyWorkSummaryProperties } from './GetMyWorkSummaryCopilotComponentProperties';

export default class GetMyWorkSummaryCopilotComponent extends ProjectIQCopilotComponentBase<IGetMyWorkSummaryProperties> {
  protected intentKey = 'GetMyWorkSummary' as const;
}
