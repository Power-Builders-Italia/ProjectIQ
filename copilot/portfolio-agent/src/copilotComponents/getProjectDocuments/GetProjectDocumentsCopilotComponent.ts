import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IGetProjectDocumentsProperties } from './GetProjectDocumentsCopilotComponentProperties';

export default class GetProjectDocumentsCopilotComponent extends ProjectIQCopilotComponentBase<IGetProjectDocumentsProperties> {
  protected intentKey = 'GetProjectDocuments' as const;
}
