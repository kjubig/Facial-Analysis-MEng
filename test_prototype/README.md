# Prototyp testowy — analiza symetrii twarzy 2D i 3D

Wstępna implementacja rdzenia systemu z pracy magisterskiej. Działa od początku do końca na
**danych zastępczych**, zanim powstanie stanowisko:

| Moduł | Wejście | Dane zastępcze w demo |
|---|---|---|
| **2D** (telefon) | zdjęcie JPG/PNG/HEIC | 5 standaryzowanych zdjęć en face z **Face Research Lab London Set** (CC BY 4.0) |
| **3D** (D455) | „zdjęcie RGB-D”: kolor + głębia wyrównana do koloru + parametry kamery | 5 **emulacji D455** tych samych osób + 3 **przypadki syntetyczne** ze znaną asymetrią |

> **Emulacja D455 to nie pomiar.** Brak publicznego zbioru RGB-D twarzy do pobrania bez wniosku
> (BIWI i VAP są niedostępne, Texas 3DFRD tylko dla kierowników projektów). Emulacja bierze siatkę
> MediaPipe ze zdjęcia (głębia *zgadywana* z 2D), renderuje ją wirtualną kamerą D455 i dodaje szum
> według wzoru Intela. Sprawdza więc **potok** 3D, a nie prawdziwą asymetrię 3D tej osoby. Poprawność
> samego algorytmu 3D sprawdzają przypadki syntetyczne (model kanoniczny MediaPipe w mm).

## Szybki start (macOS, Python 3.12 przez uv)

```bash
cd Facial-Analysis-MEng/test_prototype
uv sync                                   # tworzy .venv i instaluje biblioteki
uv run python -m core download-models     # face_landmarker.task + model kanoniczny (SHA-256)
uv run python -m core download-london     # London Set: zdjęcia en face + metadane (~35 MB)
uv run python -m core demo                # dane demo + analiza + raporty (~5 s)
open outputs/demo/index.html
uv run pytest -q                          # 23 testy
```

`uv` jest zainstalowany w `~/.local/bin` (bez zmiany profilu powłoki). Jeśli polecenie `uv` nie
działa, użyj pełnej ścieżki `~/.local/bin/uv` albo dopisz `export PATH="$HOME/.local/bin:$PATH"` do `~/.zshrc`.

## Co liczy system

**2D (zdjęcie):**
1. 478 punktów MediaPipe Face Landmarker 1.1.1 (+ 52 współczynniki mimiki, macierz pozy).
2. **Bramka jakości:** jedna twarz, wielkość i położenie, obrót / pochylenie / przechylenie
   (solvePnP ze stabilnych okolic: czoło, grzbiet nosa, kąciki oczu), oczy otwarte, mimika
   neutralna, ostrość, ekspozycja, równomierność światła. Progi wstępne w `config/default.yaml`.
3. **Punkty antropometryczne** (kandydaci z tabeli w pliku 02) i **wskaźniki**: odległości w % IPD
   i w mm (orientacyjnie, skala z tęczówki 11,7 mm), proporcje, kąty.
4. **Symetria** metodą odbicia (Klingenberg 2002): asymetria globalna (RMS, odległość Prokrustesa),
   lokalna w każdym punkcie, w parach lewa–prawa, w regionach, odchylenie punktów środkowych
   (np. brody) od osi górnej części twarzy.

**3D (RGB-D z D455):** to samo na obrazie kolorowym, a do tego:
1. punkty „podniesione” do 3D z mapy głębi (mm) i poza z punktów 3D;
2. chmura punktów twarzy i **asymetria powierzchni**: odbicie + ICP punkt–płaszczyzna z odporną
   funkcją Tukeya, mapa odległości, RMS, regiony, płaszczyzna symetrii (jak Kornreich i in. 2016);
3. **porównanie skali:** te same wymiary z tęczówki (jak w 2D) i z głębi.

Każdy wynik zapisuje **wersję**: commit, skrót konfiguracji, wersje bibliotek, sumę modelu.

## Wyniki

`outputs/<nazwa>/index.html` — tabela zbiorcza; w podkatalogach `2D_*` i `3D_*`: `raport.html`,
`wynik.json`, obrazy (`nakladka.jpg`, `glebia.jpg`, `mapa_asymetrii.jpg`) i chmura
`twarz_asymetria.ply` (MeshLab / CloudCompare). Tabele `wyniki_2D.csv` i `wyniki_3D.csv` (separator `;`).

## Własne dane (później)

**Zdjęcia z telefonu:** tylna kamera, obiektyw 2–3×, ok. 1,2–1,5 m, en face, mimika neutralna,
bez trybu portretowego i filtrów (protokół: `03_kwestie_wykonania.md`, sekcja 2). Potem:

```bash
uv run python -m core analyze-2d data/wlasne/telefon --out outputs/telefon
```

**D455:** na PC z Windows lub Linuksem uruchom `capture/capture_d455.py` (instrukcja w nagłówku
skryptu; **nieprzetestowany** — brak kamery i PC). Jedno ujęcie = katalog z `color.png`,
`depth.png` (uint16, wyrównana do koloru), `intrinsics.json`, `meta.json`. Skopiuj katalogi na Maca:

```bash
uv run python -m core analyze-3d data/wlasne/d455 --out outputs/d455
```

To są pojedyncze **ujęcia** (kolor + głębia, mediana z kilkunastu klatek), a nie nagrania wideo.

## Co sprawdzają testy (`tests/`)

| Test | Co pokazuje |
|---|---|
| `test_canonical` | Pary lewa–prawa z modelu kanonicznego są poprawne; wszystkie pary z tabeli w pliku 02 (en, ex, al, ch, zy, go) są lustrzane, a punkty środkowe leżą na osi |
| `test_geometry` | Kabsch/Umeyama, kąty, rzutowanie; solvePnP odzyskuje znaną pozę (±0,05°) |
| `test_symmetry` | Twarz symetryczna → asymetria 0; niezależność od obrotu, skali i przesunięcia; przesunięty punkt ma największą asymetrię lokalną; znak i wielkość przesunięcia brody |
| `test_surface` | 3D: twarz symetryczna bez szumu → RMS < 0,05 mm; z szumem D455 → ~0,45 mm; punkty 3D z głębi < 0,5 mm od prawdy; przesunięcie brody o 3 mm odzyskane jako 2,0–3,2 mm; wypukłość policzka po właściwej stronie |
| `test_pipeline_london` | Cały potok 2D na zdjęciu z London Set; źrenice MediaPipe < 5% IPD od ręcznego szablonu `.tem` |

## Ograniczenia (świadome)

- Punkty antropometryczne to **kandydaci** — wymagają weryfikacji wzrokowej (np. `n` = 168 leży
  raczej na wysokości kącików oczu, poniżej nasionu).
- 2D: mm tylko orientacyjnie (tęczówka ±3–4%); obrót głowy > 2° daje pozorną asymetrię.
- 3D: metoda odbicia częściowo „wchłania” asymetrię w położeniu płaszczyzny (na danych
  syntetycznych odzyskuje ok. 85–90% przesunięcia brody). Szerokość funkcji Tukeya
  (`icp_tukey_mm`) trzeba dobrać do szumu prawdziwej D455.
- Open3D 0.20 dla macOS wymaga `libusb` z Homebrew, więc geometria 3D jest napisana na numpy/scipy.
- To narzędzie badawcze, nie wyrób medyczny.

## Dane i prywatność

`data/`, `models/` i `outputs/` są w `.gitignore`. Zdjęć osób (zwłaszcza pacjentów) nie wkładamy do
repozytorium ani do usług chmurowych. London Set: DeBruine L., Jones B. (2017), *Face Research Lab
London Set*, figshare, doi:10.6084/m9.figshare.5047666.v5, licencja CC BY 4.0.

## Struktura

```
core/            pakiet: canonical, regions, landmarks, quality, features, symmetry,
                 surface (3D), emulate (D455 + syntetyka), pipeline, report, visualize, io, config
config/          default.yaml — progi, wskaźniki, parametry 3D i emulacji
capture/         capture_d455.py — nagrywanie na PC z kamerą
tests/           testy (pytest)
data/ models/ outputs/   poza gitem
```
