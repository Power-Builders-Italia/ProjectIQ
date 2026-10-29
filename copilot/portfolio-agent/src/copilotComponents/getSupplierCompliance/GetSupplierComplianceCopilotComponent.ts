import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IGetSupplierComplianceProperties } from './GetSupplierComplianceCopilotComponentProperties';

export default class GetSupplierComplianceCopilotComponent extends ProjectIQCopilotComponentBase<IGetSupplierComplianceProperties> {
  protected intentKey = 'GetSupplierCompliance' as const;
}
