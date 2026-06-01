import { render, screen } from "@testing-library/react";
import MessageMCQ from "../MessageMCQ";

describe("MessageMCQ", () => {
  it("returns null when no analysis provided", () => {
    const { container } = render(<MessageMCQ analysis={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("returns null when analysis is undefined", () => {
    const { container } = render(<MessageMCQ />);
    expect(container.firstChild).toBeNull();
  });

  it("renders correct and wrong answers", () => {
    const analysis = {
      correct_answer: "A",
      correct_reason: "Because it is right",
      wrong_answers: [
        { option: "B", reason: "Because it is wrong" },
        { option: "C", reason: "Also wrong" },
      ],
    };
    render(<MessageMCQ analysis={analysis} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
    expect(screen.getByText("Because it is right")).toBeInTheDocument();
    expect(screen.getByText("Because it is wrong")).toBeInTheDocument();
  });
});
