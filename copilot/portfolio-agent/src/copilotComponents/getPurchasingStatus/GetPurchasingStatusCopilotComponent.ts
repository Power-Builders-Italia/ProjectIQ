import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IGetPurchasingStatusProperties } from './GetPurchasingStatusCopilotComponentProperties';

export default class GetPurchasingStatusCopilotComponent extends ProjectIQCopilotComponentBase<IGetPurchasingStatusProperties> {
  protected intentKey = 'GetPurchasingStatus' as const;
}
