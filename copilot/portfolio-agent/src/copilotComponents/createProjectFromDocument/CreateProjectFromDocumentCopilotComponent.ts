import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { ICreateProjectFromDocumentProperties } from './CreateProjectFromDocumentCopilotComponentProperties';

export default class CreateProjectFromDocumentCopilotComponent extends ProjectIQCopilotComponentBase<ICreateProjectFromDocumentProperties> {
  protected intentKey = 'CreateProjectFromDocument' as const;
}
