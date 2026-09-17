# Automations

The integration fires Home Assistant events for noteworthy detections, exposes
them as **device triggers** in the automation editor, and ships four ready-made
**blueprints** that turn them into push notifications or media playback.

## Device triggers (the easy path)

Every BirdWeather device offers these triggers under **Settings → Automations →
Create → When → Device**:

| Trigger | Fires when |
| --- | --- |
| **New species detected** | An identification is first added to the station's lifetime history. |
| **Unusual visitor detected** | A species the station already knows **returns after a long absence** (default 30 days unheard; see [Tuning](#tuning-the-unusual-visitor-threshold)). |
| **Watched species detected** | A species **you chose to watch** is heard. Pick the species in **Settings → Devices & Services → BirdWeather → Configure** (a list of ones your station has detected, plus a free-text box for ones it hasn't yet). |
| **Bat detected** (`bat_detected`) | A new bat event passes the alert-confidence threshold. |
| **Searching in open space** (`bat_search_open`) | A new qualifying bat event carries this behavior code. |
| **Searching in clutter** (`bat_search_clutter`) | A new qualifying bat event carries this behavior code. |
| **Chasing** (`bat_chase`) | A new qualifying bat event carries this behavior code. |
| **Feeding buzz** (`bat_feeding_buzz`) | A new qualifying bat event carries this behavior code. |
| **Approaching** (`bat_approach`) | A new qualifying bat event carries this behavior code. |
| **Passing** (`bat_pass`) | A new qualifying bat event carries this behavior code. |

Pick the station, pick the trigger, and add whatever actions you like. The
trigger makes the detection's details available to your actions through the
event data described below.

A bat detection can fire `bat_detected` and one behavior trigger. Choose one
type if you want one notification per detection. Unknown or missing behavior
codes still allow the generic bat trigger. These events report the classifier's
result; they do not establish a confirmed species or behavior.

## Blueprints (push notification in two clicks)

Four blueprints ship as starting points: mobile notifications for new species,
unusual visitors and watched species, plus a media-player blueprint. The bat
triggers also work directly in the automation editor or through the event
example below.

- **BirdWeather — New species notification** (`new_species`) — push with the
  bird's photo, the running lifetime species count, and tap-through **action
  buttons** to eBird and Wikipedia.
- **BirdWeather — Unusual visitor notification** (`unusual_visitor`) — push that
  **attaches the call recording** when audio is enabled and the detection has a
  soundscape, falling back to the photo otherwise.
- **BirdWeather — Watched species notification** (`watched_species`) — push with
  the bird's photo for the species you've chosen in the integration's options.
- **BirdWeather — Play the call on a media player** — plays the detection's
  recording on a speaker/display; its trigger type is selectable.

Each asks which **BirdWeather station** to watch and either a **mobile-app
device** to notify or a **media player** to play on; titles/messages are
editable.

The blueprints demonstrate photos, reference links, lifetime counts and audio.
Check optional fields before using them in a custom notification: bats may
have no photo, eBird code or bird-reference links, and lifetime counts apply
only to `new_species` events.

> **Audio caveats.** `audio_url` is BirdWeather's soundscape clip (FLAC). It's
> only present when audio is enabled in the options *and* the station has a
> recording for the detection (a station with audio sharing off produces silent
> clips). FLAC may not play in iOS notification attachments or on every media
> player.
>
> Bat clips remain the original recording. A tested BAT PUC clip was 250 kHz
> FLAC; playback does not convert ultrasound to audible sound. A successful
> playback action can therefore produce no audible bat call.

### Importing a blueprint

Blueprints aren't installed with the integration — Home Assistant imports them
from a URL, one at a time. Click a badge to open the import dialog with the
blueprint pre-filled:

| Blueprint | Import |
| --- | --- |
| BirdWeather — New species notification | [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Feklundjon%2Fha-birdweather%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fbirdweather%2Fnew_species_notification.yaml) |
| BirdWeather — Unusual visitor notification | [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Feklundjon%2Fha-birdweather%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fbirdweather%2Funusual_visitor_notification.yaml) |
| BirdWeather — Watched species notification | [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Feklundjon%2Fha-birdweather%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fbirdweather%2Fwatched_species_notification.yaml) |
| BirdWeather — Play the call on a media player | [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Feklundjon%2Fha-birdweather%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fbirdweather%2Fplay_call_on_media_player.yaml) |

Prefer to do it by hand? Go to **Settings → Automations & scenes → Blueprints →
Import blueprint** and paste the blueprint's URL:

```
https://github.com/eklundjon/ha-birdweather/blob/main/blueprints/automation/birdweather/new_species_notification.yaml
https://github.com/eklundjon/ha-birdweather/blob/main/blueprints/automation/birdweather/unusual_visitor_notification.yaml
https://github.com/eklundjon/ha-birdweather/blob/main/blueprints/automation/birdweather/watched_species_notification.yaml
https://github.com/eklundjon/ha-birdweather/blob/main/blueprints/automation/birdweather/play_call_on_media_player.yaml
```

Then **Settings → Automations & scenes → Create automation → Use blueprint**,
choose the imported blueprint, and fill in the station and the device to notify.

> The bird photo is attached as the notification image. On Android it shows
> inline; on iOS it appears when you long-press / expand the notification.

## Event reference

All ten triggers are filtered views of a single bus event,
`birdweather_event`, discriminated by its `type` field. You can also trigger on
the raw event (**When → Other → Manual event**, event type `birdweather_event`)
to react to several stations at once or match on the payload yourself.

Event data:

| Field | Description |
| --- | --- |
| `type` | `new_species`, `unusual_visitor`, `watched_species`, `bat_detected`, or one of the six behavior codes above. |
| `device_id` | HA device-registry id of the station (what the device trigger filters on). |
| `station_id` | The BirdWeather station ID. |
| `device_name` | Friendly name of the station. |
| `species` | BirdWeather's identification label, which can name a broader group. |
| `species_id` | Stable BirdWeather identification ID, as a string when available. |
| `detection_id` | Stable BirdWeather event ID, as a string when available. |
| `classification` | Upstream classification, including `avian` or `bat`. |
| `scientific_name` | Scientific name. |
| `sp_code` | eBird species code; may be empty for bats. |
| `image_url` | Photo URL for the species (may be absent). |
| `audio_url` | BirdWeather soundscape clip (FLAC) for the detection, or `null` when audio is disabled or no recording exists. |
| `confidence` | Detection confidence (0–1). |
| `confidence_band` | `low` / `medium` / `high`. |
| `behavior` | Reported behavior label, when available. |
| `behavior_code` | Machine-readable behavior code, such as `bat_feeding_buzz`. |
| `behavior_confidence` | Confidence in the behavior classification, separate from identification confidence. |
| `shortlist` | Candidate records with `species_id`, `species`, `scientific_name`, `classification` and `weight`. These are alternatives for the same event, not confirmed species or extra sightings. |
| `last_seen` | Timestamp of this detection. |
| `rarity_score` | Rarity vs. the station's rarity baseline (1.0 = rarest). |
| `yearly_rank` | Rank within the rarity baseline (1 = most common). The field name mirrors the Haikubox pipeline and is kept for compatibility. |
| `days_absent` | **`unusual_visitor` only** — days since the previous sighting. |
| `lifetime_species_count` | **`new_species` only** — total distinct species ever detected at this station, including this one. |

In templates these are reached via `trigger.event.data.<field>` (for example
`{{ trigger.event.data.species }}`).

Reference URLs, alpha codes and per-identification counts belong to sensor
attributes; they are not included in the bus event.

### Example: notify on a feeding buzz

Replace `YOUR_STATION_ID` with the station's BirdWeather ID. This creates an HA
persistent notification for each qualifying feeding-buzz event:

```yaml
alias: BirdWeather feeding buzz
trigger:
  - platform: event
    event_type: birdweather_event
    event_data:
      station_id: "YOUR_STATION_ID"
      type: bat_feeding_buzz
action:
  - service: persistent_notification.create
    data:
      title: Bat feeding buzz
      message: >-
        {{ trigger.event.data.species }}:
        {{ trigger.event.data.behavior }}.
        Identification confidence:
        {{ (trigger.event.data.confidence | float(0) * 100) | round(0) }}%.
        Behavior confidence:
        {{ (trigger.event.data.behavior_confidence | float(0) * 100) | round(0) }}%.
mode: queued
max: 20
```

The API does not expose a taxonomic rank. Use `species_id` and the supplied
label in automations without assuming every bat label resolves to a species.

## Tuning the unusual-visitor threshold

`unusual_visitor` fires when a known species reappears after at least *N* days
unheard. *N* defaults to **30 days** and is set per-station in **Settings →
Devices & Services → BirdWeather → Configure → "Unusual visitor: days
unheard."**

The threshold is built on the integration's persisted last-seen history, so it
measures the real gap since the species was last heard — independent of the
rarity baseline, which makes it a more reliable alerting signal than raw rarity.

## Confidence-gating alerts

The **Only alert above confidence** option (`alert_min_confidence`) applies to
all ten triggers. It compares the detection's identification confidence, not
`behavior_confidence` or a shortlist weight. It is independent of the feed
filter that hides detections from sensors and cards. To require a minimum
behavior confidence too, add a template condition to your automation.
See [sensors.md](sensors.md#confidence).

## How the events stay quiet

The events are designed not to flood you:

- **Fresh installs are silent.** Setup pre-seeds the station's species history
  from the first 24-hour window, so bootstrapping doesn't fire a burst of
  `new_species` events for birds the station already knew about.
- **Restarts are silent for `unusual_visitor`/`watched_species`.** The first
  poll of each session only establishes a baseline; it won't replay every
  long-absent or watched bird already in the current window.
- **No re-firing while a species lingers.** For the three original species
  triggers, an identification that stays present across
  several polls fires once, not on every poll, because the events trigger on the
  *edge* of a species entering the recent window.

Bat triggers work per detection. First setup fills the bat cache and establishes
an alert watermark without replaying existing events. The watermark and IDs at
that timestamp persist in `bat_events`, so repeated polls and restarts do not
re-fire processed detections. Newer bat events can alert after a restart if they
are still in the fetched sample. Lowering the threshold does not replay events
already processed below it.

Each poll reads at most 300 detections across three pages of 100. At a busy
station, events can fall outside that sample before the next poll. The persisted
watermark prevents replay; it does not guarantee delivery of every bat event.
