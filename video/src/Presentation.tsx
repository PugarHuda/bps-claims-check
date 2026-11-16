import React from "react";
import {
  AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing,
} from "remotion";
import scenesJson from "./scenes.json";

export const FPS = 30;
const W = 1920, H = 1080;            // video
const SW = 2000, SH = 1126;          // slide PNG pixels (focus regions are in these units)
const TRANSITION = 18;               // frames of 3D slide-in at the start of each scene

type Cue = { start: number; end: number; text: string };
type Scene = { name: string; audio: string; seconds: number; cues: Cue[] };
type Region = [number, number, number, number]; // x, y, w, h in slide pixels
const FULL: Region = [0, 0, SW, SH];

// Element boxes come from the deck itself (docs/slides_regions.json, inches on a 13.333 x 7.5 in slide),
// so a redesign of the slides moves the camera with it. 150 px per inch = the 2000-px slide coordinate system.
import regionsJson from "./regions.json";
const PX_PER_IN = SW / 13.333;
const R = (slide: number, name: string): Region => {
  const r = (regionsJson as Record<string, Record<string, number[]>>)[String(slide)]?.[name];
  if (!r) return FULL;  // missing region: fall back to the whole slide rather than zooming to nowhere
  const pad = 0.12;     // a little air around the element
  return [(r[0] - pad) * PX_PER_IN, (r[1] - pad) * PX_PER_IN, (r[2] + 2 * pad) * PX_PER_IN, (r[3] + 2 * pad) * PX_PER_IN];
};

// Which slide each narration scene shows, and where the camera goes when a phrase is spoken.
// Every focus is triggered by the first subtitle cue containing the keyword, so zooms land on the spoken words.
const PLAN: Record<string, { slide: number; focus: [string, Region][]; slideSwitch?: [string, number] }> = {
  title: { slide: 1, focus: [] },
  problem: { slide: 2, focus: [] },
  pipeline: {
    slide: 3, focus: [["read.", R(3, "box1")], ["extracts", R(3, "box2")], ["evidence table", R(3, "box3")],
      ["rounds", R(3, "box4")], ["Every verdict", R(3, "caption")], ["never decide", FULL]],
  },
  headline: { slide: 4, focus: [["95.7%", R(4, "n957")], ["2.2%", R(4, "n22")], ["39", R(4, "n039")]] },
  stale: { slide: 5, focus: [["Here is one", R(5, "quote")], ["stale", R(5, "stale_row")], ["automatically", FULL]] },
  systems: {
    slide: 6, focus: [["arithmetic", R(6, "col_right_1")], ["seven false", R(6, "row_nemotron")],
      ["54", R(6, "row_rules")], ["leaked", FULL]],
  },
  humans: { slide: 7, focus: [["20 out of 20", R(7, "n2020")], ["seven sentences", R(7, "n27")], ["protocol", R(7, "protocol")]] },
  calendar: { slide: 8, focus: [["One stale", R(8, "quote_box")], ["Since 2025", R(8, "calendar_line")], ["evidence table", FULL]] },
  adoption: {
    slide: 9, focus: [["verification card", R(9, "cards_image")], ["monthly job", R(9, "monthly")], ["open.", R(9, "urls")]],
    slideSwitch: ["Thank you", 10],
  },
};

const scenes = scenesJson as Scene[];
const frames = (s: Scene) => Math.ceil(s.seconds * FPS);
export const totalFrames = () => scenes.reduce((a, s) => a + frames(s), 0);

const ink = "#161616", amber = "#b3261e";  // editorial deck: ink + one deep-red accent (name kept for the highlight)

function focusTimeline(scene: Scene): { t: number; r: Region }[] {
  const plan = PLAN[scene.name];
  const out = [{ t: 0, r: FULL }];
  for (const [kw, r] of plan.focus) {
    const cue = scene.cues.find((c) => c.text.includes(kw));
    if (cue) out.push({ t: cue.start, r });
  }
  return out.sort((a, b) => a.t - b.t);
}

// camera transform that frames region r (slide pixels) in the 1920x1080 view
function frameRegion(r: Region) {
  const [x, y, w, h] = r;
  const scale = Math.min(1.9, Math.min(SW / w, SH / h) * (r === FULL ? 1 : 0.86));
  const cx = x + w / 2, cy = y + h / 2;
  return { scale, cx, cy };
}

const Camera: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const plan = PLAN[scene.name];
  const t = frame / fps;
  const timeline = focusTimeline(scene);
  let i = 0;
  while (i + 1 < timeline.length && timeline[i + 1].t <= t) i++;
  const prev = frameRegion(timeline[Math.max(0, i - 1)].r), cur = frameRegion(timeline[i].r);
  const since = (t - timeline[i].t) * fps;
  const k = i === 0 ? 1 : spring({ frame: since, fps, config: { damping: 200, mass: 0.9 } });
  const lerp = (a: number, b: number) => a + (b - a) * k;
  // slow Ken Burns drift so full-slide holds are never static
  const drift = interpolate(frame, [0, frames(scene)], [1, 1.04]);
  const scale = lerp(prev.scale, cur.scale) * drift;
  const cx = lerp(prev.cx, cur.cx), cy = lerp(prev.cy, cur.cy);

  // 3D entrance: the slide swings in from the side, then settles with a slight tilt that relaxes
  const enter = spring({ frame, fps, config: { damping: 18, stiffness: 90 } });
  const rotY = interpolate(enter, [0, 1], [-38, 0]);
  const rotX = interpolate(frame, [0, TRANSITION * 3], [8, 0], { extrapolateRight: "clamp" });
  const z = interpolate(enter, [0, 1], [-400, 0]);

  const slide = plan.slideSwitch && scene.cues.find((c) => c.text.includes(plan.slideSwitch![0]))
    && t >= scene.cues.find((c) => c.text.includes(plan.slideSwitch![0]))!.start ? plan.slideSwitch[1] : plan.slide;

  const fit = W / SW; // slide pixels -> video pixels at scale 1
  // keep the camera inside the slide: never show the backdrop beside a zoomed-in region
  const halfW = W / 2 / (fit * scale), halfH = H / 2 / (fit * scale);
  const clamp = (v: number, lo: number, hi: number) => (lo > hi ? (lo + hi) / 2 : Math.min(hi, Math.max(lo, v)));
  const ccx = clamp(cx, halfW, SW - halfW), ccy = clamp(cy, halfH, SH - halfH);
  const tx = W / 2 - ccx * fit * scale, ty = H / 2 - ccy * fit * scale;
  const region = timeline[i].r;
  const hl = i > 0 && region !== FULL;
  const hlOpacity = hl ? interpolate(since, [6, 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;

  return (
    <AbsoluteFill style={{ perspective: 1600, backgroundColor: "#e4ded1" }}>
      <AbsoluteFill style={{ transform: `translateZ(${z}px) rotateY(${rotY}deg) rotateX(${rotX}deg)`, transformStyle: "preserve-3d" }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: SW * fit, height: SH * fit, transformOrigin: "0 0",
          transform: `translate(${tx}px, ${ty}px) scale(${scale})`,
          boxShadow: "0 30px 80px rgba(0,0,0,0.25)" }}>
          <Img src={staticFile(`slides/slide-${slide}.png`)} style={{ width: "100%", height: "100%" }} />
          {hl && (
            <div style={{ position: "absolute", left: region[0] * fit - 6, top: region[1] * fit - 6,
              width: region[2] * fit + 12, height: region[3] * fit + 12, border: `${4 / scale}px solid ${amber}`,
              borderRadius: 0, opacity: hlOpacity }} />
          )}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Subtitles: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const cue = scene.cues.find((c) => t >= c.start - 0.05 && t <= c.end + 0.25);
  if (!cue) return null;
  const local = (t - cue.start) * FPS;
  const o = interpolate(local, [0, 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 56 }}>
      <div style={{ opacity: o, background: "rgba(22,22,22,0.82)", color: "#f6f3ec", fontFamily: "Georgia, serif",
        fontSize: 42, fontWeight: 400, lineHeight: 1.25, padding: "14px 30px", borderRadius: 14, maxWidth: 1500,
        textAlign: "center", letterSpacing: 0.2 }}>{cue.text}</div>
    </AbsoluteFill>
  );
};

const Chrome: React.FC<{ index: number }> = ({ index }) => {
  const frame = useCurrentFrame();
  const done = scenes.slice(0, index).reduce((a, s) => a + frames(s), 0);
  const p = (done + frame) / totalFrames();
  return (
    <>
      <div style={{ position: "absolute", left: 0, top: 0, height: 8, width: `${p * 100}%`, background: amber }} />
      <div style={{ position: "absolute", right: 36, top: 24, fontSize: 22, letterSpacing: 1.5, textTransform: "uppercase",
        color: ink, background: "rgba(246,243,236,0.9)", fontFamily: "Arial, sans-serif", padding: "6px 14px",
        borderBottom: `1px solid #cfc8b8` }}>
        Do Their Numbers Match? · Apart AI x Epistemics Sprint
      </div>
    </>
  );
};

export const Presentation: React.FC = () => {
  let from = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "#e4ded1" }}>
      {scenes.map((s, i) => {
        const seq = (
          <Sequence key={s.name} from={from} durationInFrames={frames(s)}>
            <Camera scene={s} />
            <Audio src={staticFile(s.audio)} />
            <Subtitles scene={s} />
            <Chrome index={i} />
          </Sequence>
        );
        from += frames(s);
        return seq;
      })}
    </AbsoluteFill>
  );
};
