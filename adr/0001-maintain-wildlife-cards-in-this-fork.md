# 1. Maintain wildlife cards in this fork

Date: 2026-09-17

## Status

Accepted.

## Context and Problem Statement

This fork adds BirdWeather bat classification, behavior and candidate species to cards that upstream regenerates from a separate Haikubox repository. The current script already requires manual patches and would overwrite these features.

## Considered Options

1. Maintain the cards as source in this fork and share wildlife helpers locally
2. Keep regenerating from Haikubox and reapply BirdWeather patches
3. Change Haikubox before adding BirdWeather features

## Decision Outcome

Chosen: **option 1**.

Maintain the two existing card entrypoints and a shared wildlife module in this fork. Retire the regeneration script. Port useful upstream changes through reviewed diffs. Preserve existing card names and configuration defaults.

## Consequences

### Good

- Bat behavior and candidate displays stay tested beside the data contract.
- The fork remains buildable without another repository checkout.
- A shared local module avoids duplicating wildlife formatting logic across the two cards.

### Bad

- Upstream Haikubox card changes require deliberate porting instead of regeneration.
- This fork owns browser regression tests for both cards.

### Rejected because

- Regeneration plus manual patches can silently erase behavior and has no reliable reproduction path.
- Haikubox does not supply these BirdWeather fields, and changing another product is not necessary for this integration.
