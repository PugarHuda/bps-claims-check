"""Narration -> per-scene MP3 (Microsoft neural voice via edge-tts) + word-timed subtitle cues for Remotion.

  uv run python video/make_voice.py      # -> video/public/voice/*.mp3, video/src/scenes.json
Every number in the script is from docs/REPORT.md.
"""
import asyncio, json
from pathlib import Path

import edge_tts

VOICE = "en-US-AndrewMultilingualNeural"
OUT = Path(__file__).parent
SCENES = [
    ("title", "Do their numbers match? We checked Indonesian government statistical claims against the official "
              "figures from Statistics Indonesia, BPS. And we looked closely at what goes wrong when they don't."),
    ("problem", "Ministers and journalists quote BPS every day. Checking one claim sounds easy, but a fact checker "
                "must first decide which statistic is meant, which release, and how much rounding is fair. Get that "
                "wrong, and you publish the worst error in fact checking: a false accusation against a named official."),
    ("pipeline", "Our pipeline lets the language model do only one thing: read. It extracts the indicator, the period, "
                 "and the value exactly as stated. Then a deterministic rule takes over. It looks the figure up in an "
                 "evidence table of 104 first-release BPS numbers, each with its release URL and "
                 "date, rounds the official value to the precision of the claim, and decides. Every verdict traces to "
                 "one table row. The model can misread a sentence, but it can never decide that a number is wrong."),
    ("headline", "Across 166 sentences, 95.7% of claims could be bound to "
                 "an official figure. Only 2.2% mismatched. And government officials? Zero "
                 "mismatches out of 39."),
    ("stale", "Neither mismatch was an official misquoting BPS. Here is one. On the fourteenth of November, a news "
              "article said unemployment fell to 4.65%. That was the May figure. BPS had "
              "already published the August rate, 4.75, nine days earlier. The number was once "
              "true. It is stale. Our system detects this automatically, from the release dates in the evidence itself."),
    ("systems", "So where do automated checkers fail? Not in arithmetic. On synthetic tests every system scores "
                "100%. They fail on the frame and the period. One large model made seven false accusations, "
                "all from month on month inflation quoted as plain inflation. Hand-written rules made 54. And "
                "batched prompts even leaked numbers from one sentence into its neighbour."),
    ("humans", "Can language model labels replace a human? On 20 random sentences where every model agreed, the "
               "labels were right, 20 out of 20. But on the seven sentences where models disagreed, no "
               "labeller, frontier models included, matched the human on more than two. So the protocol is simple: "
               "let models label everything, and route every disagreement to a person."),
    ("calendar", "One stale figure fooled every model we tested. They all assumed the old BPS calendar, February "
                 "and August. Since 2025, unemployment is also released in May and November. Only an "
                 "evidence table that records when each number was released can catch that."),
    ("adoption", "We turn all of this into something fact checkers already publish: schema.org ClaimReview, with "
                 "four ratings. Matches. Right number, wrong frame. Stale. And mismatch. Every review opens a "
                 "verification card, and only human checked verdicts are public. A monthly job keeps the BPS table "
                 "current. The code, data, and report are open. Thank you."),
]


def cues(words, max_words=7, max_gap=0.45):
    """Group word boundaries into short subtitle lines; break on punctuation, length or pauses."""
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > max_gap):
            out.append(cur); cur = []
        cur.append(w)
        if w["text"][-1:] in ".,?!:" and len(cur) >= 3:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return [{"start": c[0]["start"], "end": c[-1]["end"], "text": " ".join(x["text"] for x in c)} for c in out]


def restore_punctuation(words, text):
    """Word boundaries drop punctuation; walk the original tokens in order and copy each token's surface form back."""
    import re
    norm = lambda t: re.sub(r"[^0-9a-z]", "", t.lower())
    tokens, i = text.split(), 0
    for w in words:
        for j in range(i, min(i + 4, len(tokens))):
            if norm(tokens[j]).startswith(norm(w["text"])) and norm(w["text"]):
                w["text"], i = tokens[j], j + 1
                break
    return words


async def one(name, text):
    voice_dir = OUT / "public" / "voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    for attempt in range(5):  # the free TTS endpoint occasionally returns no audio; just ask again
        words, audio = [], bytearray()
        try:
            com = edge_tts.Communicate(text, VOICE, rate="-4%", boundary="WordBoundary")
            async for chunk in com.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    s = chunk["offset"] / 1e7
                    words.append({"start": s, "end": s + chunk["duration"] / 1e7, "text": chunk["text"]})
            break
        except edge_tts.exceptions.NoAudioReceived:
            await asyncio.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"TTS failed for scene {name}")
    words = restore_punctuation(words, text)
    (voice_dir / f"{name}.mp3").write_bytes(bytes(audio))
    return {"name": name, "text": text, "audio": f"voice/{name}.mp3",
            "seconds": round(words[-1]["end"] + 0.9, 2), "cues": cues(words)}


async def main():
    scenes = [await one(n, t) for n, t in SCENES]
    (OUT / "src").mkdir(exist_ok=True)
    (OUT / "src" / "scenes.json").write_text(json.dumps(scenes, indent=1), encoding="utf-8")
    print(f"{len(scenes)} scenes, {sum(s['seconds'] for s in scenes):.0f} s total")
    for s in scenes:
        print(f"  {s['name']:9} {s['seconds']:5.1f}s  {len(s['cues'])} cues")


asyncio.run(main())
