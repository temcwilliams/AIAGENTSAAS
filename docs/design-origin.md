# Meadow Commons design record

The Agent Meadow agent floor was created for this project in `frontend/src/components/agent-floor.tsx` and the `.meadow-*` styles in `globals.css`. The terrain, reflection pond, paths, plants, station pods, handoff pavilion, and layout were authored directly as SVG, HTML, and CSS during this implementation. No floor reference repository, floor source code, screenshots, character artwork, or external 3D assets were imported.

The visual direction uses a night meadow with planted agent stations arranged around a reflection pond and connected by winding paths. Each station is an actual business agent. The handoff pavilion links to a real human-support queue. The inspector reports actual conversation/token/handoff counts. Empty workspaces show an empty meadow, not invented workers or fabricated activity. More than six agents are available through floor pagination or the accessible list view.

This milestone is an interactive isometric illustration, with keyboard-accessible HTML controls, not a WebGL 3D engine. It is intentionally lightweight for mobile devices and free hosting. A later 3D implementation can use the same tenant-scoped `/floor` API without replacing conversation, knowledge, or handoff data.

Fonts, browser controls, framework primitives, and general ideas such as agent monitoring are standard building blocks; this document records the implementation's provenance, not a claim to exclusive ownership of those general ideas.
