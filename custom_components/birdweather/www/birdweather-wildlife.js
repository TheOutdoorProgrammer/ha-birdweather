export function escapeHtml(value) {
  return String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function classification(item) {
  const value = String(item?.classification ?? "").toLowerCase();
  return value === "avian" ? "bird" : value;
}

export function filterDetections(items, value = "all") {
  if (!Array.isArray(items)) return [];
  return value === "all" ? items : items.filter((item) => classification(item) === value);
}

export function validateClassification(value = "all") {
  if (!["all", "bat", "bird"].includes(value)) throw new Error("'classification' must be all, bat, or bird");
  return value;
}

export function identity(item) {
  return String(item?.species_id || item?.sp_code || item?.scientific_name || item?.species || "");
}

export function glyph(item) {
  return classification(item) === "bat" ? "🦇" : classification(item) === "bird" || item?.sp_code ? "🐦" : "🎧";
}

export function percent(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1
    ? `${Math.round(value * 100)}%` : "";
}

export function classificationBadge(item) {
  const kind = classification(item);
  return kind === "bat" ? '<span class="wildlife-kind">🦇 Bat</span>' : "";
}

export function behaviorHtml(item) {
  if (!item?.behavior) return "";
  const confidence = percent(item.behavior_confidence);
  return `<div class="wildlife-behavior">Latest behavior: <strong>${escapeHtml(item.behavior)}</strong>${confidence ? ` <span>(${confidence} confidence)</span>` : ""}</div>`;
}

export function shortlistHtml(item) {
  if (!Array.isArray(item?.shortlist) || !item.shortlist.length) return "";
  const candidates = item.shortlist.filter((candidate) => candidate?.species || candidate?.scientific_name);
  if (!candidates.length) return "";
  return `<div class="wildlife-shortlist"><strong>Candidate identifications</strong><p>Alternatives for the latest detection, not additional sightings.</p><ul>${candidates.map((candidate) => {
    const weight = percent(candidate.weight);
    return `<li>${escapeHtml(candidate.species || candidate.scientific_name)}${weight ? ` <span>(${weight} weight)</span>` : ""}</li>`;
  }).join("")}</ul></div>`;
}

export function classificationSelector(config, hass, onChange) {
  const field = document.createElement("ha-selector");
  field.label = "Show detections";
  field.selector = { select: { mode: "dropdown", options: [
    { value: "all", label: "All wildlife" },
    { value: "bat", label: "Bats only" },
    { value: "bird", label: "Birds only" },
  ] } };
  field.value = config?.classification ?? "all";
  if (hass) field.hass = hass;
  field.addEventListener("value-changed", (event) => onChange({ classification: event.detail.value }));
  return field;
}

export const wildlifeStyles = `
  .wildlife-kind { display: inline-block; font-size: .78rem; font-weight: 600; color: var(--primary-text-color); }
  .wildlife-behavior { margin-top: 6px; font-size: .82rem; line-height: 1.4; overflow-wrap: anywhere; color: var(--secondary-text-color); }
  .wildlife-behavior strong { color: var(--primary-text-color); }
  .wildlife-shortlist { margin-top: 12px; font-size: .8rem; line-height: 1.4; overflow-wrap: anywhere; color: var(--primary-text-color); }
  .wildlife-shortlist p { margin: 3px 0; color: var(--secondary-text-color); }
  .wildlife-shortlist ul { padding-left: 20px; margin: 5px 0 0; }
  .wildlife-shortlist li + li { margin-top: 4px; }
  .wildlife-shortlist span, .audio-note { color: var(--secondary-text-color); }
  .audio-note { font-size: .75rem; line-height: 1.4; margin-top: 5px; }
`;
