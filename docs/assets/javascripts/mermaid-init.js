// Configure mkdocs-material's bundled Mermaid with Excalidraw-style hand-drawn look.
// `look: handDrawn` requires Mermaid 11+; mkdocs-material 9.5+ ships Mermaid 11.
// If the bundled version is older, the key is silently ignored — no breakage.

document$.subscribe(() => {
  if (typeof mermaid === "undefined") return;
  mermaid.initialize({
    startOnLoad: false,
    look: "handDrawn",
    theme: "neutral",
    flowchart: { curve: "basis", htmlLabels: true },
    themeVariables: {
      fontFamily: "JetBrains Mono, monospace",
      primaryColor: "#f6f6f6",
      primaryTextColor: "#1a1a1a",
      primaryBorderColor: "#1a1a1a",
      lineColor: "#1a1a1a",
    },
  });
  mermaid.run({ querySelector: ".mermaid" });
});
