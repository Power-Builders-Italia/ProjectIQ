import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IGetResourceLoadProperties } from './GetResourceLoadCopilotComponentProperties';

export default class GetResourceLoadCopilotComponent extends ProjectIQCopilotComponentBase<IGetResourceLoadProperties> {
  protected intentKey = 'GetResourceLoad' as const;
}
