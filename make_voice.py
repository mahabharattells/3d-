import asyncio, json, math, os, subprocess, sys, wave
import numpy as np
import edge_tts

VOICE = sys.argv[1] if len(sys.argv) > 1 else "en-US-AndrewMultilingualNeural"
FPS   = int(sys.argv[2]) if len(sys.argv) > 2 else 24
OUT   = os.path.abspath(sys.argv[3] if len(sys.argv) > 3 else "work")
os.makedirs(OUT, exist_ok=True)

SCRIPT_TEXT = (
    "Too impatient to wait a billion years for a diamond? "
    "Relax—scientists literally MICROWAVE one out of gas in three weeks! "
    "First, they drop a microscopic sliver of real diamond—basically diamond dandruff—inside a sealed steel chamber. "
    "Next, they pump in methane and hydrogen, then blast it with microwaves—like the world's most expensive leftover pizza! "
    "At 1,000 degrees Celsius, the gas erupts into a glowing purple plasma ball! "
    "That heat rips the gas apart, raining pure carbon atoms straight onto the tiny seed. "
    "Atom by atom, they lock into a rigid crystal grid—until three weeks later, out pops a lumpy, burnt-looking cube. "
    "Not very romantic, right? "
    "Then precision lasers shave off the ugly crust—leaving a 100% REAL diamond that even jewelers can't tell apart from a mined one!"
)

async def main():
    mp3_path = os.path.join(OUT, "vo.mp3")
    wav_path = os.path.join(OUT, "vo.wav")
    words_path = os.path.join(OUT, "words.json")
    talk_path = os.path.join(OUT, "talk_curve.json")

    comm = edge_tts.Communicate(SCRIPT_TEXT, voice=VOICE, rate="+8%", boundary="WordBoundary")
    words = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s0 = chunk["offset"] / 1e7
                dur = chunk["duration"] / 1e7
                words.append({"word": chunk["text"], "start": round(s0, 3), "end": round(s0 + dur, 3)})

    with open(words_path, "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2)

    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", mp3_path, "-ar", "16000", "-ac", "1", wav_path], check=True)

    with wave.open(wav_path, "rb") as wf:
        sr = wf.getframerate()
        n_samples = wf.getnframes()
        audio = np.frombuffer(wf.readframes(n_samples), dtype=np.int16).astype(np.float32) / 32768.0

    duration = n_samples / sr
    n_frames = int(math.ceil(duration * FPS))
    rms = []
    for i in range(n_frames):
        i0 = int((i / FPS) * sr)
        i1 = min(n_samples, int(((i + 1) / FPS) * sr))
        seg = audio[i0:i1]
        rms.append(float(np.sqrt(np.mean(seg * seg))) if len(seg) else 0.0)

    p95 = max(1e-5, float(np.percentile(rms, 95)))
    talk = [round(min(1.0, v / p95), 3) for v in rms]
    with open(talk_path, "w", encoding="utf-8") as f:
        json.dump({"duration": round(duration, 3), "fps": FPS, "n_frames": n_frames, "talk": talk}, f)

    print(f"Voiceover ready: {duration:.2f}s ({n_frames} frames @ {FPS} fps), {len(words)} words")

if __name__ == "__main__":
    asyncio.run(main())
