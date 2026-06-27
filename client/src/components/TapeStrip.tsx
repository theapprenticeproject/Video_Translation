import type { Step } from '../App';

interface TapeStripProps {
  step: Step;
  subStage: string | null;
}

// 80 deterministic waveform bar heights (0.15 – 1.0)
const BAR_COUNT = 80;
const BAR_W = 8;
const BAR_GAP = 4;
const SVG_W = BAR_COUNT * (BAR_W + BAR_GAP); // 960
const SVG_H = 52;

const BAR_HEIGHTS: number[] = Array.from({ length: BAR_COUNT }, (_, i) => {
  const a = Math.sin(i * 2.41 + 0.3) * 0.5 + 0.5;
  const b = Math.sin(i * 0.83 + 1.7) * 0.5 + 0.5;
  return 0.15 + (a * 0.6 + b * 0.4) * 0.85;
});

/** Stage definitions — progress fraction at which each stage begins */
const STAGE_DEFS: { id: Step; label: string; pct: number }[] = [
  { id: 1, label: 'Upload',    pct: 0 },
  { id: 2, label: 'Configure', pct: 0.22 },
  { id: 3, label: 'Process',   pct: 0.44 },
  { id: 4, label: 'Review',    pct: 0.72 },
  { id: 5, label: 'Export',    pct: 1.0 },
];

const SUB_STAGE_PROGRESS: Record<string, number> = {
  extracting:      0.47,
  transcribing:    0.54,
  translating:     0.61,
  awaiting_review: 0.68,
  generating_tts:  0.71,
  done:            0.72,
};

function getProgress(step: Step, subStage: string | null): number {
  if (step === 3 && subStage && subStage in SUB_STAGE_PROGRESS) {
    return SUB_STAGE_PROGRESS[subStage];
  }
  return STAGE_DEFS.find(s => s.id === step)?.pct ?? 0;
}

export default function TapeStrip({ step, subStage }: TapeStripProps) {
  const progress = getProgress(step, subStage);
  // Clip: `inset(0 RIGHT% 0 0)` — RIGHT shrinks as progress grows
  const clipRight = `${((1 - progress) * 100).toFixed(2)}%`;
  const clipStyle = { clipPath: `inset(0 ${clipRight} 0 0)` } as const;

  return (
    <div className="tape-strip" role="presentation" aria-hidden="true">
      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        preserveAspectRatio="none"
        className="tape-waveform"
        aria-hidden="true"
      >
        {/* Background bars — graphite */}
        <g>
          {BAR_HEIGHTS.map((h, i) => {
            const barH = Math.round(h * SVG_H);
            return (
              <rect
                key={i}
                className="tape-waveform__bar--bg"
                x={i * (BAR_W + BAR_GAP)}
                y={SVG_H - barH}
                width={BAR_W}
                height={barH}
                rx={1}
              />
            );
          })}
        </g>

        {/* Foreground bars — amber, clipped to progress */}
        <g className="tape-amber-group" style={clipStyle}>
          {BAR_HEIGHTS.map((h, i) => {
            const barH = Math.round(h * SVG_H);
            return (
              <rect
                key={i}
                className="tape-waveform__bar--fg"
                x={i * (BAR_W + BAR_GAP)}
                y={SVG_H - barH}
                width={BAR_W}
                height={barH}
                rx={1}
              />
            );
          })}
        </g>

        {/* Glow line — top edge of the amber fill */}
        <line
          className="tape-glow-line"
          x1={0}
          y1={0.5}
          x2={SVG_W}
          y2={0.5}
          style={clipStyle}
        />
      </svg>

      {/* Stage labels row */}
      <div className="tape-stages">
        {STAGE_DEFS.map((s) => {
          const isDone = step > s.id;
          const isActive = step === s.id;
          return (
            <div
              key={s.id}
              className={
                `tape-stage` +
                (isActive ? ' tape-stage--active' : '') +
                (isDone   ? ' tape-stage--done'   : '')
              }
            >
              <div className="tape-stage__tick" />
              <span className="tape-stage__label">{s.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
