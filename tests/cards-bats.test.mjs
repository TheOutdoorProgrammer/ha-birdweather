import assert from "node:assert/strict";
import test from "node:test";
import { filterDetections, identity, glyph, percent, behaviorHtml, shortlistHtml } from "../custom_components/birdweather/www/birdweather-wildlife.js";

const definitions = new Map();
globalThis.HTMLElement = class {
  attachShadow() {
    this.shadowRoot = { innerHTML: "", querySelector: () => ({ addEventListener() {} }), querySelectorAll: () => [] };
  }
};
globalThis.customElements = { get: (name) => definitions.get(name), define: (name, element) => definitions.set(name, element) };
globalThis.window = {};
await import("../custom_components/birdweather/www/birdweather-bird-card.js");
await import("../custom_components/birdweather/www/birdweather-details-card.js");

const bird = { species_id: "1", species: "Barn Swallow", classification: "avian", sp_code: "barswa" };
const bat = { species_id: "28", species: "Big Brown Bat", scientific_name: "Eptesicus fuscus", classification: "bat", sp_code: "", behavior: "Feeding Buzz", behavior_confidence: 0.93, shortlist: [{ species_id: "28", species: "Big Brown Bat", weight: 0.7 }, { species_id: "29", species: "Hoary Bat", weight: 0.3 }] };
const secondBat = { ...bat, species_id: "29", species: "Big Brown Bat", behavior: null, shortlist: [] };
const detections = [bird, bat, secondBat, { species: "Unclassified sound" }];

function makeCard(type, config = {}) {
  const card = new (definitions.get(type))();
  card.setConfig({ entity: "sensor.test", ...config });
  card._hass = { states: { "sensor.test": { last_updated: "now", attributes: { detections } } } };
  return card;
}

test("classification filters preserve mixed and legacy records by default", () => {
  assert.equal(filterDetections(detections), detections);
  assert.deepEqual(filterDetections(detections, "bat"), [bat, secondBat]);
  assert.deepEqual(filterDetections(detections, "bird"), [bird]);
  assert.deepEqual(filterDetections(null, "bat"), []);
});

test("empty eBird codes cannot merge distinct bat identities", () => {
  assert.notEqual(identity(bat), identity(secondBat));
  assert.equal(glyph(bat), "🦇");
  assert.equal(glyph(bird), "🐦");
  assert.equal(glyph({}), "🎧");
});

test("behavior and candidate labels separate model alternatives from detections", () => {
  assert.match(behaviorHtml(bat), /Feeding Buzz.*93% confidence/);
  assert.match(shortlistHtml(bat), /Candidate identifications/);
  assert.match(shortlistHtml(bat), /not additional sightings/);
  assert.match(shortlistHtml(bat), /70% weight/);
  assert.equal(behaviorHtml({}), "");
  assert.equal(shortlistHtml({ shortlist: [] }), "");
  assert.equal(percent(null), "");
  assert.equal(percent(2), "");
  assert.equal(percent(0), "0%");
});

test("API text is escaped in bat details", () => {
  assert.doesNotMatch(shortlistHtml({ shortlist: [{ species: '<script>alert("x")</script>' }] }), /<script>/);
  assert.match(behaviorHtml({ behavior: '<img src="x">' }), /&lt;img/);
});

test("photo-card position, URL tokens and popup follow the filtered list", () => {
  const card = makeCard("birdweather-bird-card", { classification: "bat", position: 2 });
  assert.equal(card._fillTokens("/{species_id}/{species}"), "/29/Big%20Brown%20Bat");
  let popup;
  card._openCardPopup = (config) => { popup = config; };
  card._openDetailsPopup();
  assert.equal(popup.classification, "bat");
  assert.equal(popup.position, 2);
  assert.throws(() => card.setConfig({ entity: "sensor.test", classification: "mammal" }), /classification/);
});

test("bat rows never render bird-only reference links", () => {
  const card = makeCard("birdweather-bird-list-card");
  const links = card._linkAnchors({ ...bat, ebird_url: "https://ebird.org/x", allaboutbirds_url: "https://allaboutbirds.org/x", macaulay_url: "https://macaulaylibrary.org/x", birdweather_url: "https://app.birdweather.com/x" }, { ebird: true, aab: true, ml: true, bw: true });
  assert.match(links, /BirdWeather/);
  assert.doesNotMatch(links, /eBird|All About Birds|Macaulay Library/);
});

test("list filter runs before top and keeps rows distinct with identical names", () => {
  const card = makeCard("birdweather-bird-list-card", { classification: "bat", top: 1 });
  card._render();
  assert.deepEqual(card._items, [bat]);
  assert.equal(card.getCardSize(), 3);
  card._openSpecies = identity(bat);
  assert.match(card._itemHtml(bat, 0), /class="item is-open"/);
  assert.doesNotMatch(card._itemHtml(secondBat, 1), /class="item is-open"/);
  assert.match(card._itemHtml({ ...bat, audio_url: "clip.flac" }, 0), /Original speed. Ultrasonic calls may be inaudible/);
});

test("detail popup selects the same filtered position as photo card", () => {
  const card = makeCard("birdweather-bird-list-card", { classification: "bat", position: 2, detail_only: true });
  card._render();
  assert.deepEqual(card._items, [secondBat]);
  assert.equal(card._openSpecies, "29");
});

test("a missing filtered position does not substitute a different detection", () => {
  const card = makeCard("birdweather-bird-list-card", { classification: "bat", position: 3, detail_only: true });
  card._render();
  assert.deepEqual(card._items, []);
  assert.equal(card._openSpecies, null);
});
