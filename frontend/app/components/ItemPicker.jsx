"use client";

import Link from "next/link";
import { useState } from "react";

/**
 * The problem picker, filtered by tag (FE-1).
 *
 * Client-side filtering over a list that is already fully in the HTML: the corpus is 14
 * items under L1, so paginating or fetching would add a loading state to a page that has
 * no reason to have one. If the bank ever grows past a few hundred, this is the thing to
 * revisit — and it will be obvious, because the HTML will be large.
 */
export default function ItemPicker({ tags, items }) {
  const [active, setActive] = useState(null);
  const shown = active ? items.filter((i) => i.tags.includes(active)) : items;

  return (
    <section className="picker">
      <h2>The problem bank</h2>
      <p className="hint">
        {items.length} items. Pick one to see all three arms on it.
      </p>

      <div className="tags">
        <button
          className="tag"
          aria-pressed={active === null}
          onClick={() => setActive(null)}
        >
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

      <div className="items">
        {shown.map((item) => (
          <Link key={item.id} className="item" href={`/items/${item.id}/`}>
            <div className="id mono">{item.id}</div>
            <div className="q">{item.prompt}</div>
            <div className="meta">
              {item.authored ? <span className="chip unknown">illustrative</span> : null}
              {item.planted ? <span className="chip bad">planted error</span> : null}
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
      {shown.length === 0 ? (
        <p className="notice">No items carry that tag in this build.</p>
      ) : null}
    </section>
  );
}
