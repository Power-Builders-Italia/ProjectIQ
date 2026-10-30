import { z } from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';

const wbsSchema = z.object({
  code: z.string().optional().describe('Outline code as in the document: 1 for a phase, 1.1 and 1.2 for its tasks.'),
  name: z.string().describe('Name of the phase, task or deliverable.'),
  budgetHours: z.number().optional().describe('Estimated hours, only when the document states them.'),
  startDate: z.string().optional().describe('Start date as yyyy-mm-dd, only when stated.'),
  endDate: z.string().optional().describe('End date as yyyy-mm-dd, only when stated.')
});

const propertiesSchema = z.object({
  documentName: z.string().optional().describe('File name of the document the user attached, for example Offer-2026-118.pdf.'),
  name: z.string().optional().describe('Project name or subject of the work.'),
  customer: z.string().optional().describe('Customer company as written in the document.'),
  projectManager: z.string().optional().describe('Project manager named in the document (person on the contractor side).'),
  startDate: z.string().optional().describe('Project start date as yyyy-mm-dd.'),
  endDate: z.string().optional().describe('Project end or delivery date as yyyy-mm-dd.'),
  contractValue: z.number().optional().describe('Contract or offer amount, without currency symbol.'),
  description: z.string().optional().describe('Scope of the work in two or three sentences.'),
  wbs: z.array(wbsSchema).optional().describe('Phases, tasks and deliverables of the document in their order, at most 60.')
});

export type ICreateProjectFromDocumentProperties = z.infer<typeof propertiesSchema>;

export default zodToJsonSchema(propertiesSchema);
