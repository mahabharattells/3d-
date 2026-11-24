import glob, json, os, subprocess, sys
from PIL import Image

MODE      = sys.argv[1] if len(sys.argv) > 1 else "test_sheet"
FPS       = int(sys.argv[2]) if len(sys.argv) > 2 else 24
WORK_DIR  = os.path.abspath(sys.argv[3] if len(sys.argv) > 3 else "work")
OUT_DIR   = os.path.abspath(sys.argv[4] if len(sys.argv) > 4 else "final_output")
os.makedirs(OUT_DIR, exist_ok=True)

def fmt_ass_time(sec):
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def build_ass_captions(words_json, out_ass, w, h):
    words = json.load(open(words_json, encoding="utf-8"))
    font_size = max(44, int(w * 0.072))
    margin_v  = int(h * 0.22)
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: " + str(w) + "\nPlayResY: " + str(h) + "\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,DejaVu Sans,{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,{margin_v},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = [header]
    for i in range(0, len(words), 3):
        grp = words[i:i+3]
        t0 = grp[0]["start"]
        t1 = grp[-1]["end"] + 0.08
        txt = " ".join(x["word"].upper() for x in grp)
        lines.append(f"Dialogue: 0,{fmt_ass_time(t0)},{fmt_ass_time(t1)},Default,,0,0,0,,{txt}\n")
    with open(out_ass, "w", encoding="utf-8") as f:
        f.writelines(lines)

if MODE == "test_sheet":
    shots = sorted(glob.glob(os.path.join(WORK_DIR, "frames", "shot_*.png")))
    assert shots, "No test shots found!"
    thumbs = [Image.open(p).resize((270, 480)) for p in shots[:12]]
    sheet = Image.new("RGB", (270 * 4, 480 * 3), (15, 18, 24))
    for idx, im in enumerate(thumbs):
        sheet.paste(im, ((idx % 4) * 270, (idx // 4) * 480))
    out_jpg = os.path.join(OUT_DIR, "diamond_short_12_shots.jpg")
    sheet.save(out_jpg, quality=90)
    print("Saved contact sheet:", out_jpg)
else:
    frames = sorted(glob.glob(os.path.join(WORK_DIR, "frames", "frame_*.png")))
    assert frames, "No rendered frames found!"
    im0 = Image.open(frames[0]); vw, vh = im0.size
    ass_path = os.path.join(WORK_DIR, "captions.ass")
    build_ass_captions(os.path.join(WORK_DIR, "words.json"), ass_path, vw, vh)

    out_mp4 = os.path.join(OUT_DIR, "lab_diamond_short_final.mp4")
    subprocess.run([
        "ffmpeg", "-loglevel", "error", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(WORK_DIR, "frames", "frame_%04d.png"),
        "-i", os.path.join(WORK_DIR, "vo.wav"),
        "-vf", f"ass={ass_path}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-shortest",
        out_mp4
    ], check=True)
    print(f"Final MP4 ready: {out_mp4} ({os.path.getsize(out_mp4)/1e6:.1f} MB)")
