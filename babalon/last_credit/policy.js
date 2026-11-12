// Frozen development examples. Classify the question by its requested evidence basis.
const development = {
  journal: [
    "Using the timestamps, how many deadlines were actually missed?",
    "Recount the late jobs from individual completion records.",
    "Establish the true number of missed arrivals from the event log.",
    "What count can the recorded job times substantiate?",
    "Verify the deadline count against the journal itself.",
    "Which total is supported by direct observations of arrival and completion?"
  ],
  summary: [
    "What number did the summary report?", "Quote the note's count of missed deadlines.",
    "According to the handoff, how many misses were claimed?",
    "What figure did the author write in the summary?",
    "Repeat the reported number with attribution to its source.",
    "What does the written account say about late arrivals?"
  ],
  handoff: [
    "Which count should we carry forward for this batch?",
    "Give the successor the best supported total for the current batch.",
    "What number can we rely on for the current handoff?",
    "Select the best available figure for this batch.",
    "Which supported count should travel with the successor?",
    "Carry forward the most reliable total available for this batch."
  ],
  protocol: [
    "What must the successor do before reusing this lesson?",
    "Does the protocol require a fresh observation?",
    "What obligation remains before the next worker can rely on the advice?",
    "Which rule governs reuse of the disputed lesson?",
    "What does the protocol card say about checking again?",
    "Can clearing a backlog discharge the requirement for new observation?"
  ]
};
function words(text) {
  return text.toLowerCase().match(/[a-z]+/g) || [];
}
// Equal class priors and add-one word likelihoods (multinomial naive Bayes).
const vocabulary = new Set(Object.values(development).flat().flatMap(words));
const model = Object.entries(development).map(([basis, examples]) => {
  const counts = Object.create(null);
  const tokens = examples.flatMap(words);
  for (const token of tokens) counts[token] = (counts[token] || 0) + 1;
  return {basis, counts, denominator: tokens.length + vocabulary.size};
});
function classify(question) {
  const features = words(question).filter(t => vocabulary.has(t));
  const scored = model.map(m => ({
    basis: m.basis,
    score: features.reduce((s,t) => s + Math.log(((m.counts[t] || 0) + 1) / m.denominator), 0)
  }));
  scored.sort((a,b) => b.score - a.score);
  return scored[0].basis;
}
function propose(encoded) {
  const {brief, arm, receipt} = JSON.parse(encoded);
  const intent = classify(brief.question);
  const reusable = brief.summary.batch === brief.current_batch &&
    brief.summary.measurement === "checked_recount" && brief.summary.reported_misses !== null;
  const basis = intent === "handoff" ? (reusable ? "summary" : "journal") : intent;
  const keyword = /journal|timestamp|event|completion record/i.test(brief.question);
  if (receipt === null && (arm === "always" ||
      (brief.can_inspect && ((arm === "learned" && basis === "journal") ||
                              (arm === "keyword" && keyword))))) {
    return JSON.stringify({action:"inspect", view:"timing"});
  }
  const obligation = brief.protocol_card === null ? "undetermined" : brief.protocol_card.fresh_observation;
  let value = null, citation = null;
  if (basis === "summary" && brief.summary.reported_misses !== null) {
    value = brief.summary.reported_misses;
    citation = brief.summary.id;
  }
  if (basis === "journal" && receipt && receipt.status === "REPORTED") {
    value = receipt.evidence.facts.missed_deadlines;
    citation = receipt.receipt_id;
  }
  if (basis === "protocol" && brief.protocol_card !== null) {
    value = obligation;
    citation = brief.protocol_card.id;
  }
  return JSON.stringify({action: value === null ? "abstain" : "answer",
    basis, value, citation, objection:brief.summary.open_objection, fresh_observation:obligation});
}
