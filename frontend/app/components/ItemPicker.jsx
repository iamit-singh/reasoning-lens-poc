"use client";

import Link from "next/link";
import { useState } from "react";

/**
 * The problem picker, filtered by tag (FE-1), GROUPED BY PROVENANCE (E12-D7).
 *
 * Client-side filtering over a list that is already fully in the HTML: the corpus is 14
 * items under L1, so paginating or fetching would add a loading state to a page that has
 * no reason to have one. If the bank ever grows past a few hundred, this is the thing to
 * revisit — and it will be obvious, because the HTML will be large.
 *
 * WHY THIS IS GROUPED RATHER THAN BADGED — E12-D7, three of five testers.
 * The bank mixes 14 measured runs, 10 mutated traces with a deliberately planted error and
 * 3 authored illustrations. It used to present all of them as one flat grid of near-
 * identical cards, distinguished only by a badge — and two testers read the whole thing as
 * one dataset. One put the risk precisely: "at a glance the grid looks like 27 equivalent
 * test results and I nearly took it as one." A reader who believes that has been misled
 * about the evidence by a layout decision.
 *
 * The badges were also actively working against it. `illustrative` and `planted error` were
 * styled identically to the arm chips (`direct`, `thinking`, `react`) sitting beside them,
 * so PROVENANCE and RESULT looked like the same kind of information. Grouping states the
 * provenance once, in words, above the cards it applies to — which lets the per-card
 * provenance chip go away entirely and leaves the arm chips reading as one kind of thing.
 */

// Ordered deliberately: measured first, because it is the evidence. The other two groups
// exist to be *distinguishable* from it, not to be given equal billing.
const GROUPS = [
  {
    key: "measured",
    title: "Measured runs",
    match: (i) => !i.authored && !i.planted,
    blurb:
      "Real runs at the shipping pin. These are the results; everything the site claims " +
      "about this model rests on them.",
  },
  {
    key: "planted",
    title: "Planted errors — the judge's test set, not results",
    match: (i) => i.planted,
    blurb:
      "Copies of measured traces with an error deliberately introduced, used to ask whether " +
      "the judge catches it. They measure the instrument, not the model.",
  },
  {
    key: "illustrative",
    title: "Illustrative — authored, never run",
    match: (i) => i.authored,
    blurb:
      "Hand-written fixtures that exercise states the measured corpus happens not to " +
      "contain. Nothing here was produced by the model, and no number is derived from them.",
  },
];

export default function ItemPicker({ tags, items }) {
  const [active, setActive] = useState(null);
  const shown = active ? items.filter((i) => i.tags.includes(active)) : items;
  const groups = GROUPS.map((g) => ({ ...g, items: shown.filter(g.match) })).filter(
    (g) => g.items.length > 0,
  );

  return (
    <section className="picker">
      <h2>The problem bank</h2>
      <p className="hint">
        {items.length} items, in three groups because they are not the same kind of thing:{" "}
        {GROUPS.map((g, i) => (
          <span key={g.key}>
            {i > 0 ? ", " : ""}
            <strong>{items.filter(g.match).length}</strong> {g.key}
          </span>
        ))}
        . Pick one to see all three arms on it.
      </p>

      <div className="tags">
        <button className="tag" aria-pressed={active === null} onClick={() => setActive(null)}>
          all <span className="n">{items.length}</span>
        </button>
        {tags.map(({ tag, n }) => (
          <button
            key={tag}
            className="tag"
            aria-pressed={active === tag}
            onClick={() => setActive(active === tag ? null : tag)}
          >
            {tag} <span className="n">{n}</span>
          </button>
        ))}
      </div>

      {/*
        E12-D8. These counts sum to more than the bank, because an item carries every tag
        that applies to it. Nothing said so, and on a page this insistent about numbers
        adding up, a reader who adds them finds 38 against "all 27" and concludes the
        arithmetic is broken. Saying it costs one line; the alternative is a reader
        discovering an apparent error and having to decide how much else to discount.
      */}
      <p className="hint small">
        Items carry more than one tag, so these add up to more than {items.length}.
      </p>

      {groups.map((g) => (
        <div key={g.key} className={`group group-${g.key}`}>
          <h3>
            {g.title} <span className="n">{g.items.length}</span>
          </h3>
          <p className="hint small">{g.blurb}</p>
          <div className="items">
            {g.items.map((item) => (
              <Link key={item.id} className="item" href={`/items/${item.id}/`}>
                <div className="id mono">{item.id}</div>
                <div className="q">{item.prompt}</div>
                <div className="meta">
                  {/*
                    The provenance chip that used to sit here is gone: the group heading
                    above states it once, in words, for every card beneath it. What is left
                    is arm results only, so one badge style now means one kind of thing.
                  */}
                  {item.arms.map((arm) => (
                    <span
                      key={arm.strategy}
                      className={
                        "chip " +
                        (arm.failed || arm.correct === false
                          ? "bad"
                          : arm.degraded || arm.correct === null
                            ? "unknown"
                            : "ok")
                      }
                      title={arm.label}
                    >
                      {arm.strategy}
                    </span>
                  ))}
                </div>
              </Link>
            ))}
          </div>
        </div>
      ))}

      {shown.length === 0 ? (
        <p className="notice">No items carry that tag in this build.</p>
      ) : null}
    </section>
  );
}
