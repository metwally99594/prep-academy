import { render, screen } from "@testing-library/react";
import ThinkingIndicator from "../ThinkingIndicator";

jest.mock("@/components/ui/skeleton", () => ({
  Skeleton: ({ className }) => <div className={className} data-testid="skeleton" />,
}));

describe("ThinkingIndicator", () => {
  it("renders model name", () => {
    render(<ThinkingIndicator modelName="DeepSeek Chat" />);
    expect(screen.getByText("DeepSeek Chat")).toBeInTheDocument();
  });

  it("renders skeleton elements", () => {
    const { container } = render(<ThinkingIndicator modelName="GPT-4o" />);
    const skeletons = container.querySelectorAll('[data-testid="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});
