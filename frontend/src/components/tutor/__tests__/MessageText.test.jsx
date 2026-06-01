import { render, screen } from "@testing-library/react";
import MessageText from "../MessageText";

jest.mock("react-markdown", () => ({ children }) =>
  <div data-testid="markdown">{children}</div>
);
jest.mock("remark-gfm", () => () => {});

describe("MessageText", () => {
  it("renders plain text content", () => {
    render(<MessageText content="Hallo Welt" selectedLang="de" />);
    expect(screen.getByTestId("markdown")).toHaveTextContent("Hallo Welt");
  });

  it("renders empty string", () => {
    render(<MessageText content="" selectedLang="de" />);
    expect(screen.getByTestId("markdown")).toBeInTheDocument();
  });

  it("sets RTL direction for Arabic", () => {
    const { container } = render(<MessageText content="مرحبا" selectedLang="ar" />);
    expect(container.firstChild).toHaveAttribute("dir", "rtl");
  });

  it("sets LTR direction for German", () => {
    const { container } = render(<MessageText content="Hallo" selectedLang="de" />);
    expect(container.firstChild).toHaveAttribute("dir", "ltr");
  });
});
