import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IExploreAgentCapabilitiesProperties } from './ExploreAgentCapabilitiesCopilotComponentProperties';

export default class ExploreAgentCapabilitiesCopilotComponent extends ProjectIQCopilotComponentBase<IExploreAgentCapabilitiesProperties> {
  protected intentKey = 'ExploreAgentCapabilities' as const;
}
