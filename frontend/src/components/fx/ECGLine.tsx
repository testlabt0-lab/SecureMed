/**
 * ECGLine — animated electrocardiogram (heartbeat) line.
 * A seamless repeating SVG path with a glowing stroke that sweeps via dash-offset.
 */
export default function ECGLine({
  className = '',
  stroke = '#2dd4bf',
  strokeWidth = 2.5,
  height = 64,
  opacity = 1,
  duration = 3.2,
}: {
  className?: string;
  stroke?: string;
  strokeWidth?: number;
  height?: number;
  opacity?: number;
  duration?: number;
}) {
  // One seamless heartbeat cycle across a 1000x120 viewBox
  const d =
    'M0,60 L70,60 L85,52 L100,68 L115,60 L160,60 L172,54 L184,60 ' +
    'L196,14 L208,104 L220,32 L232,60 L268,60 L282,50 L296,70 L310,60 L370,60 ' +
    'L384,54 L396,60 L408,20 L420,98 L432,36 L444,60 L480,60 L494,52 L508,68 L522,60 ' +
    'L582,60 L596,54 L608,60 L620,16 L632,102 L644,34 L656,60 L700,60 L714,50 L728,70 L742,60 ' +
    'L800,60 L814,54 L826,60 L838,22 L850,96 L862,38 L874,60 L920,60 L934,52 L948,68 L962,60 L1000,60';

  return (
    <svg
      viewBox="0 0 1000 120"
      preserveAspectRatio="none"
      style={{ height, width: '100%', opacity }}
      className={className}
      aria-hidden="true"
    >
      {/* faint full path */}
      <path d={d} fill="none" stroke={stroke} strokeWidth={strokeWidth * 0.4} opacity={0.25} />
      {/* animated sweeping path */}
      <path
        d={d}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="ecg-path"
        style={{ animationDuration: `${duration}s` }}
      />
    </svg>
  );
}
