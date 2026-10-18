import { useState } from "react";
import { useI18n } from "../i18n";
import { copyText } from "../lib/csv";
import { goLookup } from "../router";

function middle(value: string, head = 6, tail = 6): string {
  if (value.length <= head + tail + 1) return value;
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

function CopyButton({ value }: { value: string }) {
  const { t } = useI18n();
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="icon-btn"
      aria-label={done ? t("copied") : t("copy")}
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        void copyText(value).then(() => {
          setDone(true);
          window.setTimeout(() => setDone(false), 1200);
        });
      }}
    >
      {done ? (
        <span aria-hidden="true">✓</span>
      ) : (
        <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="9" y="9" width="13" height="13" rx="2" />
          <path d="M5 15V5a2 2 0 0 1 2-2h10" />
        </svg>
      )}
    </button>
  );
}

export function AddressText({
  value,
  truncate = false,
  nowrap = false,
  lookup = false,
}: {
  value: string;
  truncate?: boolean;
  nowrap?: boolean;
  lookup?: boolean;
}) {
  const shown = truncate ? middle(value) : value;
  return (
    <span className={`id-line ${truncate || nowrap ? "id-line-truncate" : ""}`}>
      {lookup ? (
        <a
          className="addr"
          href={`?a=${encodeURIComponent(value)}#/`}
          title={value}
          onClick={(event) => {
            event.preventDefault();
            goLookup(value);
          }}
        >
          {shown}
        </a>
      ) : (
        <span className="addr" title={value}>
          {shown}
        </span>
      )}
      <CopyButton value={value} />
    </span>
  );
}

export function HashText({ value }: { value: string }) {
  return (
    <span className="id-line id-line-truncate">
      <span className="addr" title={value}>
        {middle(value, 8, 8)}
      </span>
      <CopyButton value={value} />
    </span>
  );
}

export function LinkedId({ value, href }: { value: string; href: string }) {
  return (
    <span className="id-line id-line-truncate">
      <a className="addr" href={href} target="_blank" rel="noreferrer" title={value}>
        {middle(value, 8, 6)}
      </a>
      <CopyButton value={value} />
    </span>
  );
}
