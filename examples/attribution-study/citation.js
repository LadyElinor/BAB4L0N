// Extension to the frozen guest. Choose the requested source before reading its value.
function requestedSource(question) {
  const clauses = question.split(/[?!.;]+/).map(s => s.trim()).filter(Boolean);
  const request = clauses[clauses.length - 1] || question;
  if (/\b(reus(e|ing)|obligation|requirement|protocol|rule)\b/i.test(request))
    return "protocol";
  if (/\b(quote|according to|summary (claim(ed)?|report(ed)?|give)|author (said|wrote))\b/i.test(request))
    return "summary";
  if (/\b(recount|timestamp(s)?[- ]based|event tally|completion records|arrival and finish times)\b/i.test(request))
    return "journal";
  return classify(request);
}

function citedAnswer(encoded) {
  const {brief, receipt} = JSON.parse(encoded);
  const summary = brief.summary;
  const card = brief.protocol_card;
  const claim = summary.reported_misses === null ? null :
    {value:summary.reported_misses, citation:summary.id};
  const tally = receipt && receipt.status === "REPORTED" ?
    {value:receipt.evidence.facts.missed_deadlines, citation:receipt.receipt_id} : null;
  const rule = card === null ? null : {value:card.fresh_observation, citation:card.id};
  let basis = requestedSource(brief.question);
  if (basis === "handoff") {
    const usable = claim && summary.batch === brief.current_batch && summary.measurement === "checked_recount";
    basis = usable ? "summary" : "journal";
  }
  const selected = {summary:claim, journal:tally, protocol:rule}[basis];
  return JSON.stringify({action:selected ? "answer" : "abstain", basis,
    value:selected ? selected.value : null, citation:selected ? selected.citation : null,
    objection:summary.open_objection, fresh_observation:rule ? rule.value : "undetermined"});
}
