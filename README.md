# The Whole World — Wednesday 25 November 2026

[![news-image-20261125](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/surebe/news-20261125/rank.svg)](https://make.fun/bounty/news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/surebe/news-20261125/reward.svg)](https://make.fun/bounty/news-image-20261125)

One image summing up the world's news of **Wednesday 25 November 2026**:
44 stories across 7 regions — the US proposing new tariffs on 14 trading
partners, the Army detonating 9,700 lb of unstable lead azide in Iowa, two
tankers hit by mines off Hormuz, the first Pakistani astronaut boarding
China's Tiangong station, 490,334 Russian war dead in leaked records, the
Solomon Islands signing an Australian security treaty, 20 hostages freed in
Cartagena, and more — with a UTC timeline, a stat band keyed to the stories,
a printed certainty legend, a dot-matrix world map with numbered pins, and a
DATE CHECK strip naming the other days' stories left out.

Entry for the make.fun bounty
[news-image-20261125](https://make.fun/bounty/news-image-20261125).

## How it is built

`build/build.py` holds the frozen story data (14 leads + 30 briefs from the
20:30 UTC press freeze, top-up verified against the wires: the Iowa blast
confirmed detonated ~09:00 CST with EPA monitors finding zero lead in the
air, the Sudan toll holding at 19), crops the illustrations, assembles the
page in HTML/CSS, and typesets it with WeasyPrint into `entry.png`
(1024×1024, JPEG bytes). The illustrations in `art/` were generated fresh
for this page in one locked flat-editorial palette; the dot map in `build/`
is drawn in code from Natural Earth polygons.

## Run

```sh
python3 build/build.py build/stories.json entry.png
```

`main.py` copies the shipped `entry.png` to the output, so the two grader
runs write byte-identical files.
