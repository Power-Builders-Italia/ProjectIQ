import ProjectIQCopilotComponentBase from '../../shared/base/ProjectIQCopilotComponentBase';
import type { IReviewTimeApprovalsProperties } from './ReviewTimeApprovalsCopilotComponentProperties';

export default class ReviewTimeApprovalsCopilotComponent extends ProjectIQCopilotComponentBase<IReviewTimeApprovalsProperties> {
  protected intentKey = 'ReviewTimeApprovals' as const;
}
