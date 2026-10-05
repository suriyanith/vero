// Convenience aliases over the generated OpenAPI schema (src/api/schema.d.ts,
// regenerated with `npm run gen:api` — do not edit the generated file).
import type { components } from './schema'

export type Schemas = components['schemas']

export type User = Schemas['UserOut']
export type Health = Schemas['HealthOut']
export type Sample = Schemas['SampleOut']
export type RunListItem = Schemas['RunListItemOut']
export type PagedRuns = Schemas['PagedRunListItemOut']
export type RunDetail = Schemas['RunDetailOut']
export type Condition = Schemas['ConditionOut']
export type Suggestion = Schemas['SuggestionOut']
export type Quote = Schemas['QuoteOut']
export type LatestDecision = Schemas['LatestDecisionOut']
export type Decision = Schemas['DecisionOut']
export type DecisionInput = Schemas['DecisionIn']
export type AcceptHighResult = Schemas['AcceptHighOut']
export type BatchCreated = Schemas['BatchCreatedOut']
export type RunCreated = Schemas['RunCreatedOut']
export type CodeHit = Schemas['CodeOut']
export type Finding = Schemas['FindingOut']
