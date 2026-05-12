// V2 — Cockpit HUD: arc gauges instead of pure LCD, amber/cyan
// cockpit-at-night palette, artificial-horizon vario in the middle.
// Native 1080×1920.

const V2_W = 1080;
const V2_H = 1920;
const V2_AMBER = '#F0B048';
const V2_AMBER_DIM = 'rgba(240, 176, 72, 0.25)';
const V2_CYAN = '#62C8E0';
const V2_CYAN_DIM = 'rgba(98, 200, 224, 0.22)';
const V2_RED = '#E8552F';
const V2_BG = '#06090F';

// Range mappings (KSP-ish): tweak if Kerbin numbers feel off.
const SPEED_MAX = 3200;     // m/s — orbital ~2300, plenty of headroom
const G_MAX = 6.0;          // visual scale top-out at 6G

// Arc gauge: sweep from `startA` to `endA` (degrees, 0 = 3 o'clock, CW).
function ArcGauge({ cx, cy, r, startA, endA, value, max, color, thickness = 22, trackColor = 'rgba(255,255,255,0.08)' }) {
  const toRad = (d) => (d * Math.PI) / 180;
  const pct = Math.max(0, Math.min(1, value / max));
  const sweep = endA - startA;
  const valueEnd = startA + sweep * pct;

  const pathArc = (a0, a1) => {
    const x0 = cx + Math.cos(toRad(a0)) * r;
    const y0 = cy + Math.sin(toRad(a0)) * r;
    const x1 = cx + Math.cos(toRad(a1)) * r;
    const y1 = cy + Math.sin(toRad(a1)) * r;
    const large = Math.abs(a1 - a0) > 180 ? 1 : 0;
    const sweepFlag = a1 > a0 ? 1 : 0;
    return `M ${x0} ${y0} A ${r} ${r} 0 ${large} ${sweepFlag} ${x1} ${y1}`;
  };

  const ticks = [];
  const tickCount = 10;
  for (let i = 0; i <= tickCount; i++) {
    const a = startA + (sweep * i) / tickCount;
    const inner = r - thickness * 0.7;
    const outer = r + thickness * 0.35;
    const major = i % 5 === 0;
    ticks.push({
      x1: cx + Math.cos(toRad(a)) * inner,
      y1: cy + Math.sin(toRad(a)) * inner,
      x2: cx + Math.cos(toRad(a)) * outer,
      y2: cy + Math.sin(toRad(a)) * outer,
      major,
    });
  }

  return (
    <g>
      <path d={pathArc(startA, endA)} fill="none" stroke={trackColor} strokeWidth={thickness} strokeLinecap="butt" />
      <path d={pathArc(startA, valueEnd)} fill="none" stroke={color} strokeWidth={thickness} strokeLinecap="butt"
        style={{ transition: 'all 320ms cubic-bezier(0.22,0.61,0.36,1)' }} />
      {ticks.map((t, i) => (
        <line key={i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2}
          stroke={t.major ? color : 'rgba(255,255,255,0.4)'}
          strokeWidth={t.major ? 3 : 1.5} opacity={t.major ? 0.9 : 0.45} />
      ))}
    </g>
  );
}

function V2Hud({ data }) {
  const speed = useAnimatedNumber(data.speed, { duration: 320 });
  const g = useAnimatedNumber(data.g_force, { duration: 240 });
  const temp = useAnimatedNumber(data.temperature, { duration: 480 });
  const alt = useAnimatedNumber(data.altitude, { duration: 320 });
  const vspd = useAnimatedNumber(data.vertical_speed, { duration: 240 });
  const apo = useAnimatedNumber(data.apoapsis, { duration: 480 });
  const peri = useAnimatedNumber(data.periapsis, { duration: 480 });
  const missionT = useMissionClock(data.mission_time, false);

  const tColor = tempColor(temp);
  const altSplit = splitAltitude(alt);
  const apoSplit = splitAltitude(apo);
  const periSplit = splitAltitude(peri);

  return (
    <div style={{
      width: V2_W, height: V2_H, background: V2_BG, color: V2_AMBER,
      fontFamily: '"IBM Plex Mono", monospace',
      position: 'relative', overflow: 'hidden',
      padding: '56px 56px 48px', boxSizing: 'border-box',
      display: 'flex', flexDirection: 'column', gap: 26,
    }}>
      {/* Top status strip */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: `2px solid ${V2_AMBER_DIM}`, paddingBottom: 18,
      }}>
        <div>
          <div style={{ fontSize: 18, letterSpacing: '0.20em', opacity: 0.55 }}>T+</div>
          <LCD value={fmtTime(missionT)} size={42} color={V2_AMBER} ghost="rgba(240,176,72,0.10)" />
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 18, letterSpacing: '0.20em', opacity: 0.55 }}>PHASE</div>
          <div style={{ fontSize: 32, fontWeight: 600, letterSpacing: '0.08em', color: V2_AMBER, marginTop: 4 }}>
            {phaseFromData(data).toUpperCase()}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 18, letterSpacing: '0.20em', opacity: 0.55 }}>STAGE</div>
          <div style={{ fontSize: 42, fontWeight: 700, color: V2_AMBER, lineHeight: 1, marginTop: 4 }}>
            {data.current_stage}
          </div>
        </div>
      </div>

      {/* Speed circle — V1 motif applied with V2 amber palette */}
      <div style={{ position: 'relative', width: 968, height: 968, margin: '0 auto' }}>
        <svg viewBox="0 0 968 968" width="968" height="968" style={{ position: 'absolute', inset: 0 }}>
          <defs>
            <linearGradient id="v2speedGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor={V2_AMBER} />
              <stop offset="100%" stopColor={V2_CYAN} />
            </linearGradient>
          </defs>
          {/* Outer ring track */}
          <circle cx="484" cy="484" r="464" fill="none" stroke={V2_AMBER_DIM} strokeWidth="3.5" />
          {/* Animated speed progress arc — clockwise from 12 o'clock */}
          <circle cx="484" cy="484" r="464" fill="none"
            stroke="url(#v2speedGrad)" strokeWidth="8"
            strokeDasharray={`${Math.min(1, speed / SPEED_MAX) * 2 * Math.PI * 464} ${2 * Math.PI * 464}`}
            strokeDashoffset="0" strokeLinecap="round"
            transform="rotate(-90 484 484)"
            style={{ transition: 'stroke-dasharray 320ms cubic-bezier(0.22,0.61,0.36,1)' }} />
          {/* Inner ring */}
          <circle cx="484" cy="484" r="330" fill="none" stroke="rgba(240,176,72,0.42)" strokeWidth="3.5" />
          {/* Tick marks on outer ring */}
          {Array.from({ length: 12 }).map((_, i) => {
            const a = (i * 30 - 90) * Math.PI / 180;
            const x1 = 484 + Math.cos(a) * 464;
            const y1 = 484 + Math.sin(a) * 464;
            const x2 = 484 + Math.cos(a) * 446;
            const y2 = 484 + Math.sin(a) * 446;
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(240,176,72,0.55)" strokeWidth="3.5" />;
          })}
          {/* Leading-edge marker — slides around the ring with speed */}
          {(() => {
            const pct = Math.min(1, Math.max(0, speed / SPEED_MAX));
            const a = (-90 + pct * 360) * Math.PI / 180;
            const x = 484 + Math.cos(a) * 464;
            const y = 484 + Math.sin(a) * 464;
            return (
              <g style={{ transition: 'all 320ms cubic-bezier(0.22,0.61,0.36,1)' }}>
                <circle cx={x} cy={y} r="18" fill={V2_BG} stroke={V2_CYAN} strokeWidth="4" />
                <circle cx={x} cy={y} r="7" fill={V2_CYAN} />
              </g>
            );
          })()}
        </svg>

        {/* G readout (top) — removed: dedicated arc gauge below */}

        {/* VITESSE + ALT SOL center block + vario triangle */}
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: 4,
        }}>
          <div style={{
            fontFamily: '"IBM Plex Sans", sans-serif', fontWeight: 700, fontSize: 32,
            letterSpacing: '0.24em', color: V2_AMBER, opacity: 0.6,
          }}>VITESSE</div>
          <LCD value={lcdFormat(speed, { totalDigits: 7, decimals: 1 })} size={88}
            color={V2_AMBER} ghost="rgba(240,176,72,0.10)" />
          <div style={{
            fontSize: 28, opacity: 0.55, letterSpacing: '0.06em',
          }}>m / s</div>

          {/* divider */}
          <div style={{
            width: 220, height: 1, background: V2_AMBER_DIM, margin: '20px 0 14px',
          }}></div>

          <div style={{
            fontFamily: '"IBM Plex Sans", sans-serif', fontWeight: 700, fontSize: 24,
            letterSpacing: '0.24em', color: V2_AMBER, opacity: 0.6,
          }}>ALTITUDE SOL</div>
          <LCDAltitude km={altSplit.km} m={altSplit.m} size={48}
            color={V2_AMBER} ghost="rgba(240,176,72,0.10)" />
          <div style={{
            display: 'flex', gap: 122, marginTop: 2,
            fontSize: 18, opacity: 0.5, letterSpacing: '0.10em',
          }}>
            <span style={{ marginLeft: 134 }}>km</span>
            <span>m</span>
          </div>

          {/* Vario arrow + value + state label */}
          <div style={{ marginTop: 22, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
            <svg width="76" height="68" viewBox="0 0 38 34" style={{
              transform: `rotate(${vspd >= 0 ? 0 : 180}deg) scale(${1 + Math.min(0.5, Math.abs(vspd) / 500)})`,
              opacity: Math.min(1, 0.35 + Math.abs(vspd) / 200),
              transition: 'transform 320ms cubic-bezier(0.22,0.61,0.36,1), opacity 320ms',
            }}>
              <path d="M19 2 L36 30 L19 22 L2 30 Z" fill={vspd >= 0 ? V2_CYAN : V2_AMBER} />
            </svg>
            <div style={{
              fontSize: 28, color: vspd >= 0 ? V2_CYAN : V2_AMBER, letterSpacing: '0.04em',
              fontVariantNumeric: 'tabular-nums',
            }}>
              {vspd >= 0 ? '+' : ''}{vspd.toFixed(1)} m/s
            </div>
          </div>
        </div>

        {/* Temperature readout (bottom) — removed: dedicated arc gauge below */}
      </div>

      {/* G + T° bouclier — arc gauges (restored at user request) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
        <div style={{
          border: `2px solid ${V2_AMBER_DIM}`, padding: 28, position: 'relative',
        }}>
          <div style={{ fontSize: 22, letterSpacing: '0.24em', opacity: 0.55, marginBottom: 4 }}>FORCE G</div>
          <div style={{ position: 'relative', width: '100%', height: 200 }}>
            <svg viewBox="0 0 400 200" width="100%" height="200">
              <ArcGauge cx={200} cy={180} r={150} startA={180} endA={360} value={g} max={G_MAX}
                color={g > 4 ? V2_RED : V2_AMBER} thickness={22} trackColor="rgba(240,176,72,0.10)" />
            </svg>
            <div style={{
              position: 'absolute', left: 0, right: 0, bottom: 0, textAlign: 'center',
            }}>
              <LCD value={g.toFixed(2).padStart(4, '0')} size={72}
                color={g > 4 ? V2_RED : V2_AMBER} ghost="rgba(240,176,72,0.10)" />
              <span style={{ fontSize: 30, marginLeft: 10, opacity: 0.8 }}>G</span>
            </div>
          </div>
        </div>
        <div style={{
          border: `2px solid ${V2_AMBER_DIM}`, padding: 28, position: 'relative',
        }}>
          <div style={{ fontSize: 22, letterSpacing: '0.24em', opacity: 0.55, marginBottom: 4 }}>BOUCLIER</div>
          <div style={{ position: 'relative', width: '100%', height: 200 }}>
            <svg viewBox="0 0 400 200" width="100%" height="200">
              <ArcGauge cx={200} cy={180} r={150} startA={180} endA={360}
                value={Math.min(temp, 2000)} max={2000}
                color={tColor} thickness={22} trackColor="rgba(240,176,72,0.10)" />
            </svg>
            <div style={{
              position: 'absolute', left: 0, right: 0, bottom: 0, textAlign: 'center',
            }}>
              <LCD value={temp.toFixed(1).padStart(6, '0')} size={56}
                color={tColor} ghost="rgba(240,176,72,0.10)" />
              <span style={{ fontSize: 28, marginLeft: 8, color: tColor, opacity: 0.85 }}>°C</span>
            </div>
          </div>
        </div>
      </div>

      {/* Apo / Peri strip (altitude is now hero, paired with vitesse) */}
      <div style={{
        border: `2px solid ${V2_AMBER_DIM}`,
        padding: '22px 28px',
        display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 32,
      }}>
        <V2DataCell label="APOAPSE"  alt={apoSplit}  time={data.apoapsis_time} />
        <V2DataCell label="PERIAPSE" alt={periSplit} time={data.periapsis_time} />
      </div>

      {/* Stage fuel — horizontal bars */}
      <V2StageBars stages={data.stages} current={data.current_stage} />
    </div>
  );
}

function phaseFromData(d) {
  if (d.altitude < 100 && Math.abs(d.vertical_speed) < 2) return 'Pré-vol';
  if (d.altitude < 80000 && d.vertical_speed > 5) return 'Ascension';
  if (d.altitude > 70000 && Math.abs(d.vertical_speed) < 30) return 'Orbite';
  if (d.vertical_speed < -50 && d.altitude > 1000) return 'Rentrée';
  if (d.altitude < 1000 && d.vertical_speed < 0) return 'Descente';
  return '—';
}

function V2DataCell({ label, alt, time }) {
  return (
    <div>
      <div style={{ fontSize: 18, letterSpacing: '0.20em', opacity: 0.55, marginBottom: 8 }}>{label}</div>
      <LCDAltitude km={alt.km} m={alt.m} size={32} color={V2_AMBER} ghost="rgba(240,176,72,0.10)" />
      {time !== undefined && (
        <div style={{ marginTop: 8, display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <LCD value={fmtShortTime(time)} size={26} color={V2_AMBER} ghost="rgba(240,176,72,0.10)" />
          <span style={{ fontSize: 16, opacity: 0.55, letterSpacing: '0.10em' }}>arrivée</span>
        </div>
      )}
    </div>
  );
}

function V2StageBars({ stages, current }) {
  const display = [...stages].reverse();
  const labels = ['BOOSTERS', 'ÉTAGE 1', 'ÉTAGE 2', 'ÉTAGE 3'];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {display.map((s, i) => {
        const attached = s.attached;
        const pct = Math.max(0, Math.min(100, s.fuel_percent));
        const color = !attached ? 'rgba(255,255,255,0.18)'
          : pct < 15 ? V2_RED
          : pct < 30 ? V2_AMBER
          : V2_CYAN;
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{
              flex: '0 0 200px', fontSize: 22, letterSpacing: '0.12em',
              color: attached ? V2_AMBER : 'rgba(255,255,255,0.3)',
              fontWeight: attached ? 600 : 400,
            }}>{labels[i]}</div>
            <div style={{
              flex: 1, height: 28, position: 'relative',
              background: 'rgba(240,176,72,0.05)',
              border: `1.5px solid ${V2_AMBER_DIM}`,
            }}>
              <div style={{
                position: 'absolute', left: 0, top: 0, bottom: 0,
                width: `${pct}%`, background: color,
                transition: 'width 320ms cubic-bezier(0.22,0.61,0.36,1), background 240ms',
              }}></div>
            </div>
            <div style={{
              flex: '0 0 80px', textAlign: 'right',
              fontSize: 22, color: attached ? V2_AMBER : 'rgba(255,255,255,0.3)',
            }}>{attached ? `${pct.toFixed(0)}%` : '—'}</div>
          </div>
        );
      })}
    </div>
  );
}

Object.assign(window, { V2Hud, V2_W, V2_H, V2_AMBER, V2_CYAN, phaseFromData });
