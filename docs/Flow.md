# Product Flow

## 1. Arrive at landing page
- Prompt to log in
- Choose provider (GitHub, Google, etc.)
  - Provider consent → return to app → session created

## 2. Add a repo
- Choose a source:
  - Paste a public URL (public repo)
  - Pick from repository (needs connected provider access)
  - Local path / upload
- If private:
  - Grant access
  - Explain why access is needed

## 3. Start analysis
- Pick options:
  - Branch
  - How often to store snapshots
  - How far back to go
  - Exclusions
- Add multiple repos?
- Queue job

## 4. Loading
- Progress bar
- Cloning → reading history → finalising metrics

## 5. Explore results
- Overview
- Status
- Drill into files
- Packages/libraries added
- Contributors / code owners
- Timeline

## 6. Save artifacts
- PDF
- Background save job presets

## Open questions / ideas
- Cache repo (if we have enough storage), or prune the database after a time period or based on activity on the repo (if the repo is not used often, delete it)?
- Network diagram if repos / files overlap or are relevant to each other (code analysis library or small embedded model / small LLM)
