#!/usr/bin/env python3
"""
Generate vertical Quran reels from audio files + Uthmanic text.

Usage example:
python scripts/quran_reels.py \
  --audio-dir /home/mohamed-al-zeini/Documents/Quran/hazza \
  --word-file /home/mohamed-al-zeini/Documents/Quran/UthmanicHafs/UthmanicHafs1Ver09.doc \
  --font-file /home/mohamed-al-zeini/Documents/Quran/UthmanicHafs/UthmanicHafs1Ver09.otf \
  --logo /path/to/logo.png \
  --out-dir /home/mohamed-al-zeini/Documents/Quran/output_reels \
  --limit 10
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


@dataclass
class Ayah:
    index: int
    text: str
    surah: Optional[int] = None
    ayah: Optional[int] = None


def safe_run(cmd: List[str]) -> str:
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    return out.decode("utf-8", errors="replace")


def extract_text_from_word(word_file: Path) -> str:
    suffix = word_file.suffix.lower()

    if suffix in {".txt", ".md"}:
        return word_file.read_text(encoding="utf-8", errors="replace")

    if suffix == ".docx":
        try:
            import docx  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "docx parsing يحتاج python-docx: pip install python-docx"
            ) from exc
        document = docx.Document(str(word_file))
        return "\n".join(p.text for p in document.paragraphs)

    if suffix == ".doc":
        # antiword غالبا أفضل خيار خفيف لملفات doc القديمة
        try:
            return safe_run(["antiword", str(word_file)])
        except Exception as exc:
            raise RuntimeError(
                "تعذر قراءة .doc. ثبّت antiword أو حوّل الملف إلى .docx/.txt."
            ) from exc

    raise RuntimeError(f"امتداد غير مدعوم: {suffix}")


def parse_ayahs(raw_text: str) -> List[Ayah]:
    """
    Supports these line styles:
      1) surah|ayah|text
      2) surah:ayah text
      3) text only (fallback sequential)
    """
    ayahs: List[Ayah] = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        m = re.match(r"^(\d{1,3})\s*[|,:-]\s*(\d{1,3})\s*[|,:-]\s*(.+)$", line)
        if m:
            ayahs.append(
                Ayah(
                    index=len(ayahs),
                    surah=int(m.group(1)),
                    ayah=int(m.group(2)),
                    text=m.group(3).strip(),
                )
            )
            continue

        m = re.match(r"^(\d{1,3})\s*[:|,-]\s*(\d{1,3})\s+(.+)$", line)
        if m:
            ayahs.append(
                Ayah(
                    index=len(ayahs),
                    surah=int(m.group(1)),
                    ayah=int(m.group(2)),
                    text=m.group(3).strip(),
                )
            )
            continue

        ayahs.append(Ayah(index=len(ayahs), text=line))

    return ayahs


def build_lookup(ayahs: List[Ayah]) -> Tuple[Dict[Tuple[int, int], Ayah], List[Ayah]]:
    keyed: Dict[Tuple[int, int], Ayah] = {}
    sequential: List[Ayah] = []
    for a in ayahs:
        if a.surah is not None and a.ayah is not None:
            keyed[(a.surah, a.ayah)] = a
        sequential.append(a)
    return keyed, sequential


def parse_audio_surah_ayah(filename: str) -> Optional[Tuple[int, int]]:
    # Supports 001001.mp3 , 002_255.mp3 , 2-255.mp3
    stem = Path(filename).stem

    m = re.match(r"^(\d{3})(\d{3})$", stem)
    if m:
        return int(m.group(1)), int(m.group(2))

    m = re.match(r"^(\d{1,3})[_-](\d{1,3})$", stem)
    if m:
        return int(m.group(1)), int(m.group(2))

    return None


def shape_arabic(text: str) -> str:
    try:
        import arabic_reshaper  # type: ignore
        from bidi.algorithm import get_display  # type: ignore

        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        # fallback بدون تشكيل اتجاه احترافي إذا المكتبات غير مثبتة
        return text


def wrapped_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def create_frame_image(
    ayah_text: str,
    ref_text: str,
    font_file: Path,
    logo_file: Optional[Path],
    out_png: Path,
    width: int = 1080,
    height: int = 1920,
) -> None:
    bg = Image.new("RGBA", (width, height), (8, 12, 20, 255))
    draw = ImageDraw.Draw(bg)

    ayah_font = ImageFont.truetype(str(font_file), size=64)
    ref_font = ImageFont.truetype(str(font_file), size=40)

    txt = shape_arabic(ayah_text)
    lines = wrapped_text(draw, txt, ayah_font, max_width=width - 140)

    y = 360
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=ayah_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((width - tw) // 2, y), ln, font=ayah_font, fill=(248, 236, 190, 255))
        y += th + 28

    ref_shaped = shape_arabic(ref_text)
    rb = draw.textbbox((0, 0), ref_shaped, font=ref_font)
    rw = rb[2] - rb[0]
    draw.text(((width - rw) // 2, y + 60), ref_shaped, font=ref_font, fill=(214, 191, 120, 255))

    if logo_file and logo_file.exists():
        logo = Image.open(logo_file).convert("RGBA")
        max_w = int(width * 0.23)
        ratio = max_w / logo.width
        logo = logo.resize((max_w, int(logo.height * ratio)))
        lx = width - logo.width - 32
        ly = height - logo.height - 48
        bg.alpha_composite(logo, (lx, ly))

    bg.convert("RGB").save(out_png, "PNG")


def render_video(frame_png: Path, audio_file: Path, out_file: Path, fps: int = 30) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(frame_png),
        "-i",
        str(audio_file),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-tune",
        "stillimage",
        "-r",
        str(fps),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(out_file),
    ]
    subprocess.check_call(cmd)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--audio-dir", type=Path, required=True)
    p.add_argument("--word-file", type=Path, required=True)
    p.add_argument("--font-file", type=Path, required=True)
    p.add_argument("--logo", type=Path, default=None)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = args.out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    raw = extract_text_from_word(args.word_file)
    ayahs = parse_ayahs(raw)
    keyed, sequential = build_lookup(ayahs)

    audios = sorted(args.audio_dir.glob("*.mp3")) + sorted(args.audio_dir.glob("*.wav"))
    if not audios:
        raise RuntimeError("لم يتم العثور على ملفات صوت داخل audio-dir")

    if args.limit > 0:
        audios = audios[: args.limit]

    report = []
    seq_idx = 0
    for idx, audio in enumerate(audios, start=1):
        ref = parse_audio_surah_ayah(audio.name)

        if ref and ref in keyed:
            ayah = keyed[ref]
        else:
            if seq_idx >= len(sequential):
                print(f"[WARN] لا يوجد نص كافٍ للملف {audio.name}")
                continue
            ayah = sequential[seq_idx]
            seq_idx += 1

        if ref:
            ref_text = f"سورة {ref[0]} - آية {ref[1]}"
            out_name = f"{ref[0]:03d}_{ref[1]:03d}.mp4"
        else:
            ref_text = "القرآن الكريم"
            out_name = f"reel_{idx:05d}.mp4"

        frame = frames_dir / f"frame_{idx:05d}.png"
        out_video = args.out_dir / out_name

        create_frame_image(
            ayah_text=ayah.text,
            ref_text=ref_text,
            font_file=args.font_file,
            logo_file=args.logo,
            out_png=frame,
        )
        render_video(frame, audio, out_video)

        report.append({
            "audio": str(audio),
            "video": str(out_video),
            "ref": ref_text,
            "text": ayah.text[:120],
        })
        print(f"[OK] {out_video.name}")

    (args.out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Done. Generated {len(report)} videos in: {args.out_dir}")


if __name__ == "__main__":
    main()
