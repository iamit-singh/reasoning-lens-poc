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
            {/* E12 queue #3. The previous subtitle was accurate and its last clause is this
                project's integrity in one line — but as an answer to the debrief's "in your
                own words, what is this page showing?" it described **what was built**, in
                four pieces of internal vocabulary ("strategy arms", "problem bank",
                "segmented into steps", "classified and judged") inside thirty words, to
                testers the recruiting rule says are not from this project.

                It now says what was **found**, and keeps the integrity clause, which is the
                part that earns its place. It deliberately stops short of stating the insight
                B4 #9 scores: a page that hands the reader the sentence has not measured
                whether the reader reaches it, and the criterion is specifically about
                reaching it unprompted. Giving them something to reach it *with* is the fix;
                giving them the sentence would be marking our own exam. */}
            <p>
              One model, asked the same problems three different ways. Which answers held up,
              what the reasoning cost to get there — and, beside every claim, how often this
              instrument&rsquo;s own judgements were wrong.
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
