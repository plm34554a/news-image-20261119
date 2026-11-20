# The World in One Day — Thursday 19 November 2026

A make.fun entry for the competition **“Sum up 19 November's world
news in one image.”**

`main.py` is a self-contained Python program (Pillow only, no network,
no external image files) that draws a 1024×1024 front-page newspaper
collage and writes it as a PNG. Every panel is drawn in code:

- **Top story** — the International Court of Justice ruling at The
  Hague that Myanmar committed genocide against the Rohingya
  (Gambia v. Myanmar, 9–6), with courthouse columns and scales.
- **Trump, Putin & Xi meet in Shenzhen** — the APEC trilateral summit,
  its “Declaration Toward Peace,” and talks dominated by Ukraine,
  with US, Russian and Chinese flags over a summit table.
- **COP31 in Antalya** — ministers racing to unblock the climate
  talks in Türkiye, with a sun, globe and thermometer.
- **Van Gogh sells for $190.4M** — an artist auction record, with a
  swirly starry-night motif.
- **Trump pardons Pete Rose** — a posthumous pardon for the baseball
  legend, with a stitched baseball.
- **Senate rejects the Iran war-powers bill 51–48** and the **Hormuz
  crisis** — the IEA's energy-security warning, with an oil tanker
  in a strait.
- A briefs strip: the EU's proposed €45bn loan for Ukraine, violence
  in 28 districts of Bangladesh, Bukele seeking a third term in
  El Salvador, and the death of Fiona the hippo at Cincinnati Zoo.

## Run it

```sh
python3 main.py                 # writes /output/entry.png
python3 main.py out/entry.png   # or any output path you choose
```

Requires Python 3.13 with Pillow. The output is deterministic —
no timestamps or randomness are embedded — so repeated runs produce
a byte-identical PNG (1024×1024, under 1 MiB).

## License

MIT — see `LICENSE`.
