/**
 * BrandMark.tsx
 * -------------
 * The logo mark: an 18650 cell with a pulse line running through it.
 */

export default function BrandMark({ size = 42 }: { size?: number }) {
  const icon = Math.round(size * 0.57);
  return (
    <span
      aria-hidden="true"
      className="grid flex-none place-items-center bg-linear-135 from-cobalt to-ion shadow-[0_8px_24px_-6px_rgba(59,108,255,0.65),inset_0_1px_0_rgba(255,255,255,0.35)]"
      style={{ width: size, height: size, borderRadius: Math.round(size * 0.31) }}
    >
      <svg
        width={icon}
        height={icon}
        viewBox="0 0 24 24"
        fill="none"
        stroke="#ffffff"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="7" y="4" width="10" height="17" rx="3" />
        <path d="M10.5 2h3" />
        <path d="M2 13h5.5l1.8-3.5 2.7 7 2-4.5H22" />
      </svg>
    </span>
  );
}
