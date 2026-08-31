import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { App } from "./App";

it("renders the minimal product identity without product functionality", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: "TopologyProof" })).toBeVisible();
  expect(screen.getByText("Agentic Falsification of Hidden Deployment Assumptions")).toBeVisible();
  expect(screen.getByRole("button", { name: "ANALYZE PATCH" })).toBeInTheDocument();
});
