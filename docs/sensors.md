# Sensors

All entities are grouped under a single device per BirdWeather station. Entity IDs are prefixed with your device name (e.g. `sensor.backyard_*`). There are 17 detection and activity sensors, one binary sensor, and conditional PUC hardware sensors.

## The sensors

| Entity | State | Notable attributes |
|---|---|---|
| `sensor.recent_detections` | Species count in the current 1-hour window | `detections` (one per species, ranked by recency) |
| `sensor.recent_bats` | Distinct bat identifications in the configured recent window (default 1 hour) | `detections` (bat-only, ranked by recency) |
| `sensor.last_bat_detection` | Most recently heard bat identification, regardless of age | `detections` (bat-only rolling cache of 50 events, persisted across restarts and outages) |
| `sensor.last_detection` | Most recently heard species — the last detection regardless of age (persists across restarts/outages) | `detections` (one per event — rolling cache of the most recent 50, newest first; **survives outages**) |
| `sensor.daily_count` | True total detections over the trailing 24 h (BirdWeather's native count) | — (numeric total) |
| `sensor.daily_top_species` | Number of species in the trailing 24 h | `detections` (ranked by 24 h count) |
| `sensor.notable_species` | Most "notable" species in the last 24 h (tunable rarity/recency blend); **`unknown` when none observed** | `detections` (ranked by notability — drains with the 24 h window) |
| `sensor.new_species` | Most recently first-detected species | `detections` (lifetime history — most recent 50 first-seen), `lifetime_species_count` |
| `sensor.yearly_top_species` | Number of species in the rarity baseline | `detections` (ranked by baseline count) |
| `sensor.rarest_species` | Number of species, rolling 7 d | `detections` (ranked by rarity) |
| `sensor.lifetime_species` | Distinct species ever detected at this station | — (plain count; `MEASUREMENT` for long-term statistics) |
| `sensor.species_diversity` | Shannon diversity index (H′) over the last 24 h | `richness` (species count), `evenness` (Pielou H′/ln S, 0–1) |
| `sensor.activity_level` | Today's volume ÷ a typical day (1.0 ≈ normal, 2.0 ≈ twice as busy); **`unknown` until a baseline exists** | `detections_today`, `typical_daily_count` |
| `sensor.new_species_window` | How many species were first heard here in the last 30 days (discovery momentum) | — |
| `sensor.history_start` | **Diagnostic** — the station's earliest recorded detection (a timestamp) | — |
| `sensor.watched_species` | How many of your watch-list species the station has recorded | `detections` (your watched species, most-recently-heard first) |
| `sensor.peak_activity_hour` | The station's busiest hour of the day, over the trailing 7 days | `hourly_activity` (24-bucket curve), `peak_hour` |

### Bat sensors

`recent_bats` counts distinct identification IDs in the recent feed window,
not individual passes or a count of animals. It uses the same configurable
window and feed-confidence filter as `recent_detections` and returns zero when
no qualifying bats remain in that window.

`last_bat_detection` has its own persisted 50-event cache. Daytime bird activity
cannot evict its last bat. Its state is `unknown` until a qualifying bat has
been observed; after that, it keeps the last bat through quiet periods,
restarts and outages. A failed poll can still mark the entity `unavailable`.

These sensors include only records whose `classification` is `bat`. Existing
station-wide sensors and native counts retain their scope, including birds and
bats as returned by BirdWeather. Feed-based sensors see at most 300 recent
events per poll, so busy stations can have gaps even within the selected window.

BirdWeather may identify a broader group rather than a species. The API does
not provide a taxonomic rank; the integration preserves its label and does not
claim a more specific identification.

### `sensor.lifetime_species`

A running count of every distinct species the station has ever detected — your "life list." It only rises (the lifetime `seen_species` log never shrinks) and carries a `MEASUREMENT` state class, so Home Assistant's long-term statistics chart it as a curve climbing over weeks and months. The same number is also exposed as the `lifetime_species_count` attribute on `new_species` for templates.

### Activity & discovery sensors

These summarise *how* active and varied the station is, computed from BirdWeather's **true** native per-period counts (not the detection-feed sample):

- **`species_diversity`** — the Shannon diversity index (H′) over the last 24 h: ~0 when one species dominates, higher when many species are heard evenly. `richness` (how many species) and `evenness` (Pielou's H′/ln S, 0–1) ride along as attributes.
- **`activity_level`** — today's detection total divided by a typical day (the mean over the trailing 30-day baseline): `1.0` is a normal day, `2.0` twice as busy, `0.5` half. `unknown` until there's a baseline. `detections_today` and `typical_daily_count` are exposed as attributes.
- **`new_species_window`** — how many species were first heard here in the last 30 days — a "discovery momentum" counter, high on a new install and settling toward 0 as the station learns the local regulars. (The window is tunable — see [advanced.md](advanced.md).)
- **`peak_activity_hour`** — the hour of the day the station is busiest, over the trailing 7 days, rendered as a time (e.g. `07:00`). The full 24-bucket `hourly_activity` curve is an attribute for chart cards.
- **`history_start`** *(diagnostic)* — a timestamp of the station's earliest recorded detection (BirdWeather's `earliestDetectionAt`), useful context for the activity/lifetime figures.

## Binary sensors

| Entity | Device class | On when |
|---|---|---|
| `binary_sensor.extended_silence` | `problem` | The station has logged **no** detections in the trailing 24 hours |

### `binary_sensor.extended_silence`

A station going a full day with zero detections almost always signals a real problem — offline, unpowered, or a failed microphone/connection — rather than a genuinely silent day. This `problem` binary sensor turns **on** in that case so you can alert on it directly. It's derived from the trailing-24 h `detections_24h` list. When a poll fails entirely the integration goes `unavailable` (see [api.md](api.md#failure-handling)) and this sensor goes unavailable too — "we don't know" rather than a false alarm. It lives in the device's Diagnostic section.

## PUC hardware sensors

For BirdWeather **PUC** stations the integration also creates onboard hardware sensors — but only the sub-suites your station actually reports (a BirdNET-Pi or other software station gets none). They're created from the first poll's data:

| Entity | Suite | Notes |
|---|---|---|
| `sensor.temperature` | environment | °C |
| `sensor.humidity` | environment | % |
| `sensor.barometric_pressure` | environment | hPa |
| `sensor.sound_pressure_level` | environment | dB |
| `sensor.voc` | environment | BME688 bVOCeq, ppm |
| `sensor.air_quality_index` | environment | BSEC IAQ (0–500) |
| `sensor.light_level` | light | broadband `clear` channel (luminance proxy) |
| `sensor.battery_voltage` | system | V *(diagnostic)* |
| `sensor.power_source` | system | e.g. USB-C *(diagnostic)* |
| `sensor.wifi_signal` | system | dBm *(diagnostic)* |
| `sensor.sd_card_free` | system | % free, with `free_gb`/`capacity_gb` attributes *(diagnostic)* |

## The `detections` contract

Every list-bearing sensor exposes a `detections` attribute. Records include
`species`, `species_id`, `classification`, `scientific_name`, `sp_code`,
`image_url`, `last_seen` and `rank`, where available. Identification IDs remain
stable when bird-specific metadata is missing. `classification` includes
`avian` and `bat`; `sp_code`, alpha codes and photos can be empty for bats.

Event records also carry `detection_id`, identification `confidence`,
`confidence_band`, `behavior`, `behavior_code`, `behavior_confidence` and a
`shortlist` of candidate identifications. Each candidate contains `species_id`,
`species`, `scientific_name`, `classification` and `weight`. The weights are
alternative classifier results for one detection, not extra sightings. A
collapsed identification record carries the latest event's behavior and shortlist;
aggregate-only records may have no event metadata.

Other optional fields include `audio_url`, `alpha`/`alpha6`, photo attribution,
and reference URLs. Bird-only links (`ebird_url`, `allaboutbirds_url`,
`macaulay_url`) are omitted for bats; available BirdWeather and Wikipedia links
remain usable. Audio is the original recording, with no ultrasound conversion.

`rank` is a 1-based list position assigned by that sensor's ordering, not a
taxonomic rank:

| Sensor | `rank` 1 is | Basis |
|---|---|---|
| `recent_detections` | most recently heard | `last_seen` desc |
| `recent_bats` | most recently heard bat identification | `last_seen` desc |
| `last_detection` | most recent event | `last_seen` desc |
| `last_bat_detection` | most recent bat event | `last_seen` desc |
| `notable_species` | most notable | `notability_score` desc (rarity ↔ recency blend) |
| `new_species` | most recently first-seen | `first_seen` desc |
| `daily_top_species` | most detected in 24 h | 24 h `count` desc |
| `yearly_top_species` | most detected in the baseline window | baseline `count` |
| `rarest_species` | rarest in the last 7 days | `rarity_score` desc |
| `watched_species` | most recently heard | `last_seen` desc |

Any of these can drive the `birdweather-bird-list-card`. The recent lists use
the configured window, and `notable_species` uses the trailing 24 hours. Those
lists empty as detections age out; `notable_species` then becomes `unknown`.
Both last-detection sensors use persisted event caches instead.

### Per-species vs. per-event, live vs. persisted

The lists on `last_detection` and `last_bat_detection` contain individual
events. Each keeps up to 50 events, newest first, in a separate persisted cache.
Other lists group detections by identification; repeated events collapse into
one record with a count and the most recent timestamp. Feed counts represent
the sampled events, while native aggregate lists use BirdWeather's counts.

The recent and notable lists are live windows. `new_species.detections` keeps
the latest first-seen identifications from the lifetime log, and both
last-detection lists persist independently of the current window.

## Rarity scoring

`notable_species` and `rarest_species` score each species against the station's own rarity baseline — BirdWeather's `topSpecies` counts over a trailing window (default **1 month**, tunable; see [advanced.md](advanced.md)). A species absent from that window scores `1.0` (capped — tied with the rarest known species rather than overshooting); the most-detected species scores near `0`. So a Cooper's Hawk scores as more unusual at a station that rarely records raptors than at one that hears them daily.

## Notability tuning

`notable_species` blends rarity with recency:

> `notability_score = w · rarity_score + (1 − w) · recency_score`

`recency_score` is a linear decay over the trailing 24 hours — a detection right now scores 1.0; one at the 24-hour edge scores 0.0. The weight `w` is a slider in the integration's options (Settings → Devices & Services → BirdWeather → Configure):

- **100% rarity** — pure rarity; the list is dominated by the rarest species and changes slowly.
- **0% rarity** — pure recency; the top is whatever was heard most recently.
- **70% rarity** (default) — mostly rarity-driven, with enough recency that a fresh sighting can dethrone an old long-tail entry.

Changes take effect immediately — saving the options form reloads the entry, no waiting for the next poll.

## Confidence

BirdWeather reports identification confidence from 0 to 1. The integration
derives a low/medium/high `confidence_band`. In the top-level options, the feed
filter hides low-confidence detections from feed-based sensors and cards; the
independent alert filter gates device triggers, including bat and behavior
triggers. `alert_min_confidence` uses identification confidence, not
`behavior_confidence` or a shortlist weight. Native 24-hour totals and diversity
counts are unaffected by the feed filter.

## Persistent state

Both last-detection sensors restore their caches on startup. The bat store
also keeps the alert watermark and IDs at that timestamp to avoid replaying
processed events. `notable_species` empties after 24 hours without a qualifying
detection; `new_species` persists through the lifetime first-seen log.

Data written to `.storage/` (seven files per station; see [architecture.md](architecture.md)):

| Store file | Contents |
|---|---|
| `birdweather.<station_id>.seen_species` | Lifetime first-detection log |
| `birdweather.<station_id>.last_seen` | Species → most recent detection timestamp |
| `birdweather.<station_id>.yearly` | The rarity baseline (`topSpecies` ranks) |
| `birdweather.<station_id>.seven_day` | Per-day rarity records for the 7-day `rarest_species` window |
| `birdweather.<station_id>.recent_events` | Rolling cache of the 50 most recent events (backs `last_detection`) |
| `birdweather.<station_id>.bat_events` | Rolling cache of 50 bat events and persisted alert watermark |
| `birdweather.<station_id>.species_meta` | Species IDs, classification and per-identification lookups (codes, scientific names, images, attribution, links) |
