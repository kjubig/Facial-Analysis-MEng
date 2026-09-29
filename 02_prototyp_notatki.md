# Prototyp pipeline'u 3D — notatki z pierwszej analizy

**Data:** 29.09.2026
**Skan:** „Infinite” head scan, Lee Perry-Smith / Infinite-Realities (CC BY 3.0), wersja z przykładów three.js
**Kod:** `scripts/analyze_scan.py`, pakiet `src/facial3d/`
**Wyniki:** `outputs/lee_perry_smith/` (rysunki + `report.json`, niecommitowane)

> Cel: zrozumieć problem na jednym skanie, przechodząc przez zadania 3–5 (punkty → płaszczyzna → asymetria → proporcje). **Jeden skan nie pozwala na żadne wnioski o populacji ani o atrakcyjności** — poniższe liczby służą do oceny *metody*, nie twarzy.

---

## 1. Pipeline

1. Wczytanie siatki + tekstury, render frontalny ortograficzny (odpowiednik klatki RGB kamery RGB-D).
2. MediaPipe Face Landmarker (478 punktów) na renderze → **podniesienie do 3D** przez rzutowanie promieni na siatkę (odpowiednik odczytu mapy głębi).
3. Skala: skan nie ma jednostek → skalowanie przez założone IPD = 64 mm.
4. Trzy definicje płaszczyzny pośrodkowej: (a) MNK przez 28 punktów linii środkowej, (b) Procrustes konfiguracji 220 par bilateralnych, (c) odbicie powierzchni + ICP.
5. Symetryczne przycięcie twarzy (owal MediaPipe, punkt i jego odbicie muszą być wewnątrz).
6. Mapa odchyleń, RMSD ważone polem, % powierzchni w tolerancji; osobno dla tercji.
7. Asymetria par punktów, wybrane proporcje, symulacja szumu kamery głębi.

## 2. Ustalenia

### 2.1 Skala metryczna to problem pierwszego rzędu
- Skan ma umowne jednostki. Skala z IPD: **51,4 mm/jedn.** (środki szpar powiekowych, render z teksturą) vs **54,3 mm/jedn.** (punkty tęczówki, render bez tekstury) — **~5% różnicy** z samego wyboru punktów, plus ±8% z samego założenia IPD.
- Oczy na skanie są **zamknięte** → punkty tęczówki MediaPipe (468–477) są zgadywane; wyłączone z analizy symetrii.
- **Wniosek dla pracy:** metryczna głębia z kamery + wzorzec kalibracyjny w każdej sesji (rozdz. 6.3 przeglądu) nie są opcjonalne.

### 2.2 MediaPipe działa na samej geometrii
- Twarz wykryta także na renderze **bez tekstury** (szare cieniowanie). Różnica położeń 2D tekstura vs geometria: **mediana 2,0 mm, p90 3,8 mm, max 4,9 mm**.
- To argument za wariantem „tylko geometria” (RODO, rozdz. 10.2 przeglądu), ale też sygnał, że **niepewność punktów jest tego samego rzędu co mierzona asymetria** (~1–3 mm) → potrzebny test powtarzalności detekcji.

### 2.3 Podniesienie punktów do 3D — nieciągłości głębi
- Pojedynczy promień w szczelinie ust trafia do jamy ustnej: błąd **88,8 mm**. To dokładnie problem „flying pixels” kamer głębi. Rozwiązanie: wysoki percentyl głębokości w otoczeniu punktu (`SurfaceRaycaster.lift_robust`).
- **Punkty przy sylwetce są niewiarygodne w widoku frontalnym:** 35/468 punktów widzianych pod kątem > 75°, w tym **zygion, gonion, exocanthion**. Przed filtrowaniem para gonionów dawała „asymetrię” 36,5 mm.
- **Wniosek dla zadania 2 (stanowisko):** jedna kamera frontalna nie zmierzy wiarygodnie punktów bocznych (szerokość twarzy, żuchwa). Opcje: 2–3 kamery / obrót głowy, albo jawne ograniczenie zestawu cech.

### 2.4 Wybór płaszczyzny pośrodkowej zmienia wynik o ~65%

| Płaszczyzna | Kąt do ICP | RMSD [mm] | % pow. < 1 mm |
|---|---|---|---|
| MNK linii środkowej | 1,20° | 2,16 | 36% |
| Procrustes par | 1,30° | 1,81 | 50% |
| Odbicie + ICP | — | **1,31** | **79%** |

- Płaszczyzna z linii środkowej daje mapę z gradientem „czerwone z jednej strony, niebieskie z drugiej” — to sygnatura **obrotu płaszczyzny**, nie asymetrii twarzy (`04_planes_compared.png`).
- ICP daje najmniejszą asymetrię **z konstrukcji** (minimalizuje to samo kryterium) — czyli częściowo „wchłania” prawdziwą asymetrię (zgodne z [5]). Niższa liczba ≠ lepsza metoda.
- **Potwierdza rozdz. 4.3 przeglądu empirycznie** — definicja płaszczyzny musi być jawną, uzasadnioną decyzją metodyczną.

### 2.5 Asymetria regionalna (płaszczyzna ICP)

| Tercja | RMSD [mm] | % < 1 mm |
|---|---|---|
| górna | 2,00 | 63% |
| środkowa | 1,23 | 77% |
| dolna | 1,05 | 87% |

Uwaga: „górna tercja” to tylko pas czoła — owal MediaPipe kończy się poniżej linii włosów, a postrzępiona krawędź przycięcia (niska rozdzielczość siatki) zawyża wynik. Trichion nie jest dostępny w MediaPipe.

### 2.6 Symulacja szumu kamery głębi (20 powtórzeń)

| σ szumu [mm] | RMSD [mm] | kąt płaszczyzny [°] |
|---|---|---|
| 0 | 1,31 | 0 |
| 0,5 | 1,42 | 0,06 |
| 1,0 | 1,66 | 0,10 |
| 1,5 | 1,96 | 0,12 |
| 2,0 | 2,26 | 0,34 |

- Przy szumie typowym dla taniej kamery (1,07–1,48 mm wg [8]) **RMSD rośnie o 27–50%**, a płaszczyzna prawie się nie zmienia (0,1°).
- **To obciążenie systematyczne, nie losowe** — szum zawsze *dodaje* asymetrię, więc nie znosi się przy powtórzeniach pomiaru. Wniosek: uśrednianie wielu klatek (fuzja czasowa) przed analizą + raportowanie „progu szumu” stanowiska. Bezpośrednio pod PB1.

### 2.7 Proporcje (tylko ilustracyjnie, 1 osoba, przybliżone mapowanie Farkasa)

| Wskaźnik | Wartość | „Kanon” |
|---|---|---|
| g–sn : sn–gn | 0,92 | 1,0 |
| sn–sto : sto–gn | 0,40 | 0,5 |
| en–en : en–ex (P / L) | 1,27 / 1,25 | 1,0 |
| al–al : en–en | 1,05 | 1,0 |
| ch–ch : al–al | 1,12 | 1,5 (neoklas.) / 1,618 (φ) |

## 3. Ograniczenia tego skanu
- ~9,3 tys. wierzchołków; region twarzy 2346 wierzchołków / 272 cm² (odstęp ~3,4 mm) — za mało na analizę sub-milimetrową.
- Skan artystyczny: nieznana obróbka (wygładzanie, retusz).
- Mapowanie MediaPipe → Farkas niezwalidowane.

## 4. Proponowane następne kroki
1. **Dane populacyjne:** złożyć wnioski o zbiór badawczy (FaceScape / Headspace / BU-3DFE / Florence / Stirling ESRC) — bez populacji nie ma DA/FA, Mahalanobisa ani PB2–PB3.
2. **Powtarzalność detekcji punktów** (tanie, od razu): renderować ten sam skan z małymi perturbacjami (obrót ±5°, oświetlenie, rozdzielczość) → rozrzut punktów → symulowany test–retest.
3. **Walidacja mapowania Farkasa** — z definicjami z Farkas (1994), rozdz. 13 przeglądu.
4. **Decyzja o płaszczyźnie pośrodkowej** — do omówienia z promotorem (propozycja: Procrustes par jako definicja główna, ICP jako analiza wrażliwości).
5. Rozważyć rejestrację szablonową (template-based, preferowaną w [5]).
