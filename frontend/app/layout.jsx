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
            <p style={{ marginTop: 8 }}>
              <a href="/calibration/" style={{ fontSize: 13 }}>
                Calibration &amp; limitations →
              </a>
            </p>
          </div>
        </header>
        <main className="wrap">{children}</main>
      </body>
    </html>
  );
}
