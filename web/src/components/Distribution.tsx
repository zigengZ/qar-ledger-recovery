import { useEffect, useRef, useState } from "react";
import type { Overview } from "../data/types";
import { useI18n } from "../i18n";
import { formatCount } from "../lib/format.mjs";

const HIST_BINS: { label: string; from: string[] }[] = [
  { label: "<0.001", from: ["to_0_001"] },
  { label: "0.001–0.01", from: ["to_0_01"] },
  { label: "0.01–0.1", from: ["to_0_1"] },
  { label: "0.1–1", from: ["to_1"] },
  { label: "1–10", from: ["to_10"] },
  { label: "10–100", from: ["to_100"] },
  { label: "100–1000", from: ["to_1k"] },
  { label: ">1000", from: ["to_10k", "to_100k", "above_100k"] },
];

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function Histogram({ overview }: { overview: Overview }) {
  const { t, theme } = useI18n();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let disposed = false;
    const charts: { dispose: () => void; resize: () => void }[] = [];
    const onResize = () => charts.forEach((chart) => chart.resize());
    window.addEventListener("resize", onResize);
    const ink = cssVar("--ink");
    const muted = cssVar("--muted");
    const line = cssVar("--line");
    const byId = new Map(overview.histogram.map((bin) => [bin.id, bin.count]));
    const bins = HIST_BINS.map((bin) => ({
      label: bin.label,
      count: bin.from.reduce((sum, id) => sum + (byId.get(id) ?? 0), 0),
    }));

    void import("../lib/echarts").then(({ default: echarts }) => {
      if (disposed || !ref.current) return;
      const chart = echarts.init(ref.current);
      charts.push(chart);
      chart.setOption({
        backgroundColor: "transparent",
        tooltip: { trigger: "axis" },
        grid: { left: 44, right: 8, top: 16, bottom: 48 },
        xAxis: {
          type: "category",
          data: bins.map((bin) => bin.label),
          axisLabel: { color: ink, fontSize: 11, rotate: 40 },
          axisLine: { lineStyle: { color: line } },
        },
        yAxis: {
          type: "value",
          name: t("hist_count"),
          nameTextStyle: { color: muted, fontSize: 11 },
          axisLabel: { color: muted, fontSize: 11 },
          splitLine: { lineStyle: { color: line } },
        },
        series: [
          {
            type: "bar",
            data: bins.map((bin) => bin.count),
            itemStyle: { color: "#c46b3a", borderRadius: [5, 5, 0, 0] },
            barMaxWidth: 28,
          },
        ],
      });
    });

    return () => {
      disposed = true;
      window.removeEventListener("resize", onResize);
      charts.forEach((chart) => chart.dispose());
    };
  }, [overview, theme, t]);

  return <div ref={ref} className="mt-2 h-52 w-full" />;
}

export function Distribution({ overview }: { overview: Overview }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  return (
    <details className="card px-4 py-3" onToggle={(event) => setOpen((event.currentTarget as HTMLDetailsElement).open)}>
      <summary className="cursor-pointer text-sm font-semibold">{t("histogram")}</summary>
      <p className="mt-2 text-sm text-muted">{t("histogram_hint", { zero: formatCount(overview.zero) })}</p>
      {open ? <Histogram overview={overview} /> : null}
    </details>
  );
}
