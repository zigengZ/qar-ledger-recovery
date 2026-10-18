import { useI18n } from "../i18n";
import { displayGroup } from "../lib/roles";

const TONE: Record<string, { light: string; dark: string }> = {
  wallet: { light: "#0b5b4a", dark: "#b7f0e2" },
  pool: { light: "#1d4e86", dark: "#c5d9f5" },
  lock: { light: "#8a3e16", dark: "#f6d0b0" },
  process: { light: "#3d4a34", dark: "#d7e0cb" },
  unknown: { light: "#5c564c", dark: "#e6dfd2" },
};

export function RoleBadge({ role }: { role: string }) {
  const { t, theme } = useI18n();
  const group = displayGroup(role);
  const tone = TONE[group] ?? TONE.unknown;
  const color = theme === "dark" ? tone.dark : tone.light;
  return (
    <span className="role-badge" style={{ color, borderColor: color }} title={t(`tip_${group}`)}>
      {t(`group_${group}`)}
    </span>
  );
}
