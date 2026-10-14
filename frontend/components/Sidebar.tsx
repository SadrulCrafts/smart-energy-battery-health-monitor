/**
 * Sidebar.tsx
 * -----------
 * Logo, section links and a small device card. On narrow screens it becomes a
 * top bar with the links in a scrollable row.
 */

import BrandMark from "./BrandMark";

type IconName = "grid" | "chart" | "list" | "pulse";

const LINKS: { label: string; href: string; icon: IconName }[] = [
  { label: "Overview", href: "#top", icon: "grid" },
  { label: "Live chart", href: "#voltage", icon: "chart" },
  { label: "Readings", href: "#readings", icon: "list" },
  { label: "SoH model", href: "#soh", icon: "pulse" },
];

function NavIcon({ name }: { name: IconName }) {
  const common = {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.9,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  switch (name) {
    case "grid":
      return (
        <svg {...common}>
          <rect x="3" y="3" width="7" height="9" rx="2" />
          <rect x="14" y="3" width="7" height="5" rx="2" />
          <rect x="14" y="12" width="7" height="9" rx="2" />
          <rect x="3" y="16" width="7" height="5" rx="2" />
        </svg>
      );
    case "chart":
      return (
        <svg {...common}>
          <path d="M3 3v18h18" />
          <path d="m7 15 4-5 3 3 5-6" />
        </svg>
      );
    case "list":
      return (
        <svg {...common}>
          <path d="M8 6h13M8 12h13M8 18h13" />
          <path d="M3 6h.01M3 12h.01M3 18h.01" />
        </svg>
      );
    case "pulse":
      return (
        <svg {...common}>
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
      );
  }
}

interface SidebarProps {
  deviceId: string | null;
  deviceKind: string | null;
  apiVersion: string | null;
  online: boolean;
  alertCount: number;
}

export default function Sidebar({ deviceId, deviceKind, apiVersion, online, alertCount }: SidebarProps) {
  return (
    <aside
      aria-label="Main navigation"
      className="flex flex-col gap-4 border-b border-line bg-side px-4 py-4 backdrop-blur-xl lg:sticky lg:top-0 lg:h-screen lg:gap-8 lg:border-r lg:border-b-0 lg:px-[18px] lg:py-[26px]"
    >
      <a href="#top" className="flex items-center gap-3 no-underline" style={{ color: "inherit" }}>
        <BrandMark />
        <span className="flex flex-col leading-tight">
          <span className="font-display text-[15px] font-semibold tracking-tight">Battery Health</span>
          <span className="font-display text-[13px] text-ink-2">Monitor</span>
        </span>
      </a>

      <nav className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-0.5 lg:flex-col lg:gap-1 lg:overflow-visible">
        {LINKS.map((link, index) => (
          <a
            key={link.href}
            href={link.href}
            aria-current={index === 0 ? "page" : undefined}
            className={
              "flex min-h-11 flex-none items-center gap-3 rounded-xl px-3 text-[14.5px] no-underline transition-colors " +
              (index === 0
                ? "bg-active text-ink shadow-[inset_0_0_0_1px_var(--active-line)]"
                : "text-ink-2 hover:bg-hover hover:text-ink")
            }
          >
            <NavIcon name={link.icon} />
            <span>{link.label}</span>
            {link.href === "#readings" && alertCount > 0 && (
              <span
                className="ml-auto grid h-[22px] min-w-[22px] place-items-center rounded-full bg-warn-bg px-1.5 text-xs font-semibold text-warn-ink"
                aria-label={`${alertCount} alerts in view`}
              >
                {alertCount}
              </span>
            )}
          </a>
        ))}
      </nav>

      <div className="mt-auto hidden flex-col gap-1.5 rounded-2xl border border-line bg-panel p-3.5 lg:flex">
        <div className="flex items-center gap-2 text-sm font-medium">
          <span
            aria-hidden="true"
            className={"size-2 rounded-full " + (online ? "animate-live bg-good" : "bg-muted")}
          />
          {deviceId ?? "No device yet"}
        </div>
        {deviceKind && <div className="text-[13px] text-muted">{deviceKind}</div>}
        {apiVersion && <div className="text-[13px] text-muted">API version {apiVersion}</div>}
      </div>
    </aside>
  );
}
