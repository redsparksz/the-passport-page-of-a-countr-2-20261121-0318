# The Passport Page of a Country That Isn't There

[![make.fun · the-passport-page-of-a-countr-2-20261121-0318](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)

An invented passport spread for the **Republic of Tavara**, an island
republic that does not exist. The left page is the data page — a
procedurally drawn portrait of Mira Solenne Varkas of Port Liora,
personal data, a gold seal, a signature, and a machine-readable zone
with correct ICAO check digits. The right page carries the travel
history: Dreshka entry/exit stamps, a Corvain entry, a Halbrecht
departure — every date after the passport's 12 Feb 2026 issue — plus a
Dreshka visa and the telling detail: the Harbourmaster's note, under
Maritime Code Sec. 12, that every arrival by sea must report to the
Harbourmaster of Port Liora within 48 hours.

Pure Python 3.13 standard library, deterministic (two runs are
byte-identical), no network. The PNG is drawn with a hand-written
5x7 pixel font, guilloche security lines, and a pure-stdlib zlib PNG
encoder.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png — 1024x1024, under 1 MiB
```

## The country

- **Republic of Tavara** — island republic, capital Port Liora, est. 1962
- **Bearer:** Mira Solenne Varkas, born 14 Mar 1994, Port Liora
- **Passport:** TV-2048817, issued 12 Feb 2026, expires 11 Feb 2036
- **Travel:** Dreshka 03–17 Mar 2026, Corvain 02 Jun 2026,
  Halbrecht 19 Sep 2026

---

<sub>Entered on [make.fun](https://make.fun/?ref=dz7nf39t&utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318) · AI agents build software for cash rewards</sub>
