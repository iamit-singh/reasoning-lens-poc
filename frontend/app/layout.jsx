import "./globals.css";

export const metadata = {
  title: "Reasoning Lens",
  description:
    "An instrument that makes a model's reasoning measurable rather than merely visible.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <header className="masthead">
          <div className="wrap">
            <a href="/">
              <h1>Reasoning Lens</h1>
            </a>
            <p>
              Three strategy arms over one problem bank, segmented into steps, each step
              classified and judged — with the agreement numbers published beside every claim.
            </p>
            <p style={{ marginTop: 8, display: "flex", gap: 18, flexWrap: "wrap" }}>
              <a href="/calibration/" style={{ fontSize: 13 }}>
                Calibration &amp; limitations →
              </a>
              {/* FE-5. Linked from the shell rather than buried, because the negative
                  result it carries is a finding this project wants read, not a page it
                  keeps in case anyone asks. */}
              <a href="/faithfulness/" style={{ fontSize: 13 }}>
                Faithfulness →
              </a>
            </p>
          </div>
        </header>
        <main className="wrap">{children}</main>
      </body>
    </html>
  );
}
