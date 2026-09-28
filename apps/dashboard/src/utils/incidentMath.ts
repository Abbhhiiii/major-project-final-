export const visualProbability = (confidence: number, impact: number) => .65 * confidence + .35 * impact

export const effectiveReliability = (reliability: number, ageMs: number) => (
  reliability * Math.exp(-Math.log(2) * ageMs / 10_000)
)
