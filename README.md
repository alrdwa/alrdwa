- 👋 Hi, I’m @alrdwa
- 👀 I’m Developer & Linux Homelab Enthusiast 
- 🌱 I’m Full-Stack Developer & Language Specialist
- 💞️ I’m Crafting mobile experiences with Flutter and backend scripts with Python. Passionate about self-hosting, automation, and the future of AI.
- 📫 How to reach me : Egypt +02 01122526119

<!---
alrdwa/alrdwa is a ✨ special ✨ repository because its `README.md` (this file) appears on your GitHub profile.
You can click the Preview link to take a look at your changes.
--->

## Quran Reels generator (local)

This repository now includes a helper script to generate vertical Quran recitation reels from:

- ayah text file (`.doc`, `.docx`, `.txt`)
- audio files (`.mp3` / `.wav`)
- Uthmanic font (`.otf`)
- optional logo (`.png`)

### Script

- `scripts/quran_reels.py`

### Example run

```bash
python scripts/quran_reels.py \
  --audio-dir /home/mohamed-al-zeini/Documents/Quran/hazza \
  --word-file /home/mohamed-al-zeini/Documents/Quran/UthmanicHafs/UthmanicHafs1Ver09.doc \
  --font-file /home/mohamed-al-zeini/Documents/Quran/UthmanicHafs/UthmanicHafs1Ver09.otf \
  --logo /path/to/logo.png \
  --out-dir /home/mohamed-al-zeini/Documents/Quran/output_reels \
  --limit 10
```

### Dependencies

```bash
pip install pillow arabic-reshaper python-bidi
```

If your Word file is `.docx`, optionally install:

```bash
pip install python-docx
```

If your Word file is old `.doc`, install `antiword` on your machine.
