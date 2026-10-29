import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IGetPortfolioHealthProperties } from './GetPortfolioHealthCopilotComponentProperties';

export default class GetPortfolioHealthCopilotComponent extends ProjectIQCopilotComponentBase<IGetPortfolioHealthProperties> {
  protected intentKey = 'GetPortfolioHealth' as const;
}
