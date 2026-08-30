import type React from "react";

/** Render the minimal TopologyProof application identity. */
export function App(): React.JSX.Element {
  return (
    <main className="app-shell">
      <p className="eyebrow">Deployment assumption verification</p>
      <h1>TopologyProof</h1>
      <p className="tagline">Agentic Falsification of Hidden Deployment Assumptions</p>
    </main>
  );
}
