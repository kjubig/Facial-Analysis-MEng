# Przegląd literatury — wersja 1.0

**Praca:** System do standaryzowanej analizy symetrii, harmonii i percepcji atrakcyjności twarzy
**Autor:** Łukasz
**Data:** 12.09.2026
**Status:** wersja robocza do konsultacji z promotorem

> **Jak czytać ten dokument.** Rozdziały 2–10 to materiał, który po redakcji stanie się rozdziałem 2 pracy („Przegląd literatury"). Rozdziały 11–13 to część robocza: tabela porównawcza, wnioski dla projektu systemu i lista rzeczy do doczytania. Wszystkie cytowane pozycje zostały zweryfikowane pod kątem danych bibliograficznych (autorzy, rocznik, DOI) — nie ma tu pozycji „z pamięci".

---

## 1. Metodyka przeglądu

Przegląd objął cztery obszary tematyczne, wynikające bezpośrednio z zadań 1–7:

| Obszar | Zapytania | Źródła |
|---|---|---|
| A. Percepcja atrakcyjności — podstawy | *facial attractiveness*, *symmetry averageness sexual dimorphism* | Annual Review of Psychology, Scientific Reports, Evolution and Human Behavior |
| B. Proporcje i kanony | *golden ratio*, *neoclassical canons*, *facial proportions validity* | Maxillofacial Plastic and Reconstructive Surgery, J. Oral Maxillofac. Surg. |
| C. Analiza asymetrii 3D | *3D facial asymmetry*, *mirroring ICP*, *template-based registration* | European Journal of Orthodontics, Progress in Orthodontics, Diagnostics |
| D. Metody obliczeniowe | *facial beauty prediction*, *MediaPipe Face Mesh*, *depth camera anthropometry* | ICPR, WACV, Computers & Graphics, Journal of Dentistry, arXiv |

Kryteria włączenia: prace recenzowane, dostępne pełne dane bibliograficzne, publikacje po 2015 r. **z wyjątkiem** pozycji kanonicznych (Rhodes 2006) oraz prac definiujących narzędzia (Kartynnik 2019, Li 2017). Świadomie włączono także prace **negatywne / krytyczne** — bez nich przegląd byłby jednostronny, a to właśnie one wyznaczają realną lukę badawczą.

---

## 2. Ramy pojęciowe: co właściwie mierzymy

### 2.1 Trzy klasyczne predyktory atrakcyjności

Klasyczny model ewolucyjny, podsumowany przez Rhodes [1], wskazuje trzy cechy morfologiczne przewidujące ocenę atrakcyjności twarzy:

1. **Symetria** (symmetry) — im mniejsza asymetria fluktuacyjna, tym wyższa ocena.
2. **Uśrednienie** (averageness) — im bliżej „przeciętnej" populacyjnej kształtu twarzy, tym wyższa ocena.
3. **Dymorfizm płciowy** (sexual dimorphism) — femininity u kobiet, masculinity u mężczyzn.

Rhodes [1] uznaje wszystkie trzy za wsparte empirycznie, choć zaznacza, że efekty są umiarkowane i częściowo skorelowane.

### 2.2 Rewizja: symetria może nie być tym, za co ją uważamy

**To jest najważniejsze pojedyncze ustalenie tego przeglądu dla naszej pracy.** Lee, Li, Rafiee, Jones i Shiramizu [2] (*Scientific Reports* 2025) przebadali 100 twarzy ocenianych przez 400 osób, stosując liniowe modele mieszane, w których **jednocześnie** kontrolowano asymetrię, dystynktywność (odwrotność uśrednienia) i dymorfizm płciowy. Wyniki:

- **uśrednienie** — istotnie przewiduje atrakcyjność u obu płci,
- **kobiecość rysów** — istotnie przewiduje atrakcyjność twarzy kobiecych,
- **męskość rysów** — brak istotnego efektu dla twarzy męskich,
- **symetria — brak istotnego efektu dla obu płci.**

Wniosek metodologiczny: wcześniejsze silne korelacje symetria–atrakcyjność mogły wynikać z tego, że symetrii **nie kontrolowano względem uśrednienia** (twarze bardziej średnie są zwykle bardziej symetryczne — te dwie cechy są ze sobą splątane).

> **Konsekwencja dla pracy magisterskiej.** Tytuł pracy zestawia „symetrię, harmonię i percepcję atrakcyjności" — literatura sugeruje, że **to nie jest jedna oś, tylko trzy osobne, słabo powiązane wymiary**. To nie jest problem dla pracy; to jest jej najlepsza teza. System nie powinien zakładać, że „symetryczna = atrakcyjna", tylko **mierzyć te wymiary niezależnie i empirycznie sprawdzić siłę ich powiązania** na własnych danych 3D. To odróżnia pracę inżynierską od kolejnego „kalkulatora złotego podziału".

### 2.3 Asymetria fluktuacyjna vs kierunkowa

W literaturze antropometrycznej rozróżnia się:

- **asymetrię kierunkową (DA, directional asymmetry)** — systematyczne, populacyjne odchylenie w jedną stronę (np. lekko większa prawa połowa twarzy jest normą),
- **asymetrię fluktuacyjną (FA, fluctuating asymmetry)** — losowe odchylenia osobnicze od symetrii dwustronnej; to FA jest teoretycznym nośnikiem „jakości rozwojowej",
- **antysymetrię** — rzadka w twarzy.

Większość prac inżynierskich raportuje surową „asymetrię" bez rozdzielenia DA i FA. **Rozdzielenie tych składowych to konkretny, obronny wkład metodyczny**, który można zrealizować w tej pracy: DA szacujemy jako średnią wektorów asymetrii w całej próbie, FA jako odchylenie osobnicze od tej średniej.

### 2.4 „Harmonia" — pojęcie bez standardowej definicji

Uwaga terminologiczna, ważna przy pisaniu pracy: **„harmonia twarzy" nie ma ustalonej definicji operacyjnej w literaturze**. W piśmiennictwie chirurgiczno-ortodontycznym używa się jej zamiennie z „balansem", „proporcjonalnością" lub całościowym wrażeniem estetycznym. Nie znaleziono pracy definiującej harmonię jako mierzalną wielkość odrębną od symetrii i proporcji.

**Propozycja definicji operacyjnej na potrzeby pracy** (do zaakceptowania przez promotora):

> *Harmonia* = zgodność zestawu proporcji twarzy z rozkładem referencyjnym danej populacji, wyrażona jako odległość Mahalanobisa wektora cech proporcjonalnych badanego od centroidu populacji referencyjnej.

Takie ujęcie ma trzy zalety: (a) jest jednoznacznie obliczalne, (b) łączy „harmonię" z dobrze udokumentowanym predyktorem *averageness*, (c) automatycznie uwzględnia kowariancję cech — czego nie robi liczenie pojedynczych wskaźników.

---

## 3. Kanony proporcji: złoty podział i kanony neoklasyczne

### 3.1 Złoty podział — stan dowodów

Naini [3] (*Maxillofacial Plastic and Reconstructive Surgery* 2024) przeprowadza systematyczną krytykę tezy o złotym podziale (φ ≈ 1,618) w estetyce twarzy. Kluczowe punkty:

- przypisywanie φ Euklidesowi, Pacioliemu czy Leonardowi jako kanonu **ludzkiego piękna** jest historycznie nieprawdziwe,
- teza w chirurgii twarzy wywodzi się w praktyce z prac Rickettsa (1982), nie ze źródeł klasycznych,
- badania „potwierdzające" zwykle zaczynają od założenia φ i szukają pomiarów, które je potwierdzają (błąd konfirmacji),
- konkluzja autora: *„currently no evidence to support the use of the golden ratio in orthognathic or facial aesthetic/reconstructive surgical planning"*.

### 3.2 Test empiryczny na danych 3D

Zwahlen, Tang, Leung i Tan [4] wykonali bezpośredni test: 163 sędziów (62 pacjentów ortognatycznych, 101 laików) oceniało 30 rotujących modeli 3D twarzy w skali VAS 0–100 (obrazy przekonwertowane na czarno-białe, by wyeliminować wpływ karnacji). Na twarzach zmierzono **77 parametrów**: złoty podział, kanony neoklasyczne, „idealne" proporcje i kąty.

Wyniki:
- **42/77 parametrów u kobiet i 32/77 u mężczyzn istotnie odbiegało od wartości „idealnych"** — w populacji zdrowych studentów,
- **tylko ok. 14% parametrów (6 proporcji, 8 kątów, 1 kanon neoklasyczny, 1 proporcja) korelowało istotnie z oceną atrakcyjności.**

### 3.3 Wniosek dla projektu systemu

Kanony klasyczne **nie mogą być używane jako ground truth** („odchylenie od φ = brzydota"). Mogą i powinny być natomiast używane jako **cechy wejściowe** modelu, którego zadaniem jest empiryczne ustalenie, które z nich cokolwiek wnoszą. To jest różnica między systemem naukowym a aplikacją typu „face rating".

Praktycznie: warto policzyć pełen zestaw kanonów (trójpodział twarzy, pięciopodział szerokości, kanony neoklasyczne Farkasa, wskaźniki φ), a następnie zastosować analizę ważności cech (permutation importance / SHAP) i pokazać, które przetrwały. **Negatywny wynik też jest wynikiem** i będzie spójny z [3] i [4].

---

## 4. Ilościowa analiza asymetrii twarzy

### 4.1 Systematyczny przegląd metod automatycznych

Peng, Qu, Zhang i Lin [5] (*European Journal of Orthodontics* 2026) to najświeższy i najbardziej bezpośrednio przydatny przegląd — 14 kwalifikujących się prac, metody podzielone na **cztery kategorie**:

| Kategoria | Zasada | Zalety | Wady |
|---|---|---|---|
| **Landmark-based** | Odległości/kąty między odpowiadającymi sobie punktami po obu stronach względem płaszczyzny pośrodkowej | Prosta, szybka, interpretowalna | Bardzo ograniczona próbka informacji (kilkanaście–kilkadziesiąt punktów) |
| **Depth-stratified** | Porównanie map głębi lewej i prawej połowy w warstwach | Nie wymaga landmarków | Wrażliwa na ustawienie głowy; wciąż ograniczony zakres danych |
| **Original-mirror alignment** | Lustrzane odbicie skanu, rejestracja ICP do oryginału, mapa odległości | Analiza całej powierzchni, brak zależności od landmarków | **Błędy przy silnej asymetrii** — ICP „rozkłada" błąd po całej twarzy |
| **Template-based** | Dopasowanie wspólnego szablonu anatomicznego, transfer korespondencji, rejestracja ważona | Najbardziej odporna; poprawna korespondencja anatomiczna | Największa złożoność implementacyjna |

Wnioski autorów: metody **template-based są preferowane**, original-mirror stanowi praktyczną alternatywę dla asymetrii łagodnej; walidacje wykazują umiarkowane–silne współczynniki korelacji i minimalną zmienność pomiarową. Jako kierunki dalszych badań autorzy wskazują wprost: **automatyzację uczeniem głębokim, analizę dynamiczną i dostępne narzędzia kliniczne**.

> **To jest bezpośrednie zaproszenie do tematu naszej pracy.** Praca oparta o tanią kamerę głębi, z automatyczną detekcją punktów i otwartym pipeline'em, trafia dokładnie w lukę zdefiniowaną przez [5].

### 4.2 Metryki asymetrii — co raportować

Na podstawie [5] i prac pokrewnych, minimalny sensowny zestaw:

- **RMSD** (root mean square deviation) między oryginałem a lustrzanym odbiciem po rejestracji — globalna miara skalarna,
- **procent powierzchni w tolerancji** (np. |d| < 0,5 mm / < 1,0 mm / < 2,0 mm) — bardziej informacyjny niż sama średnia,
- **kolorowa mapa odchyleń** — obowiązkowa jakościowa wizualizacja,
- **wskaźniki landmarkowe** — odległość punktów parzystych od płaszczyzny pośrodkowej, asymetria kątowa,
- **asymetria regionalna** — osobno dla tercji górnej / środkowej / dolnej; asymetria w twarzy jest silnie regionalna, wartość globalna ją maskuje.

### 4.3 Kluczowy problem techniczny: płaszczyzna pośrodkowa

Wszystkie metody landmark-based zależą od wyznaczenia płaszczyzny pośrodkowej (midsagittal plane), a jej definicja **nie jest jednoznaczna** — wyznaczana z landmarków linii środkowej, przez dopasowanie symetrii metodą najmniejszych kwadratów, albo z osi bezwładności. Różne definicje dają różne wartości asymetrii dla tej samej twarzy. **Wybór i uzasadnienie tej definicji musi być jawnym elementem metodyki pracy** — to typowe pytanie na obronie.

---

## 5. Detekcja punktów charakterystycznych

### 5.1 MediaPipe Face Mesh

Kartynnik, Ablavatski, Grishchenko i Grundmann [6] (arXiv:1907.06724, CV4ARVR @ CVPR 2019) opisują model będący podstawą MediaPipe Face Mesh: sieć predykująca **468 punktów 3D** powierzchni twarzy z pojedynczego obrazu RGB, działająca w czasie rzeczywistym na GPU urządzeń mobilnych.

**Ograniczenia, które trzeba wprost opisać w pracy:**

1. **468 punktów to nie są punkty antropometryczne.** To wierzchołki gęstej siatki topologicznej. Klasyczne punkty Farkasa (nasion, pronasale, subnasale, gnathion, zygion…) trzeba do nich **odwzorować**, a odwzorowanie to jest przybliżone i powinno zostać zwalidowane.
2. **Współrzędna z jest quasi-metryczna.** MediaPipe estymuje głębokość w skali względnej, powiązanej z szerokością twarzy, a nie w milimetrach. **Dokładnie tu wchodzi kamera głębi** — dostarcza rzeczywistą, metryczną trzecią współrzędną. To jest techniczne uzasadnienie użycia kamery głębi w tej pracy i warto je jasno wyartykułować.
3. Model jest trenowany głównie na twarzach frontalnych; dokładność spada przy dużych rotacjach.

Alternatywy do rozważenia i porównania: **3DDFA-V2** (dopasowanie 3DMM, lepsze przy rotacji), **dlib 68** (baseline 2D), **FLAME** [7] jako model parametryczny kształtu i ekspresji uczony z 4D skanów (ACM TOG 2017), **DECA** dla rekonstrukcji z pojedynczego obrazu.

W badaniu porównawczym landmarkerów w warunkach zabiegowych (cytowanym za: Hammadi i in., *Sensors* 2022, doi:10.3390/s22186850) rekomendowano **3DDFA-V2** jako najodpowiedniejszy tam, gdzie pacjent porusza głową w różnych kierunkach — MediaPipe wypadał gorzej poza pozycją frontalną. *(pozycja do zweryfikowania w oryginale — patrz rozdz. 13)*

---

## 6. Akwizycja obrazu: kamery głębi i standaryzacja stanowiska

To materiał bezpośrednio pod **zadanie 2** (stanowisko).

### 6.1 Ile realnie wynosi błąd taniej kamery głębi

| Praca | Sprzęt | Referencja | Wynik |
|---|---|---|---|
| ten Harkel i in. [8], *Sci Rep* 2017 | Intel RealSense F200 | 3dMD (stereofotogrametria, dokł. 0,20–0,25 mm) | Dokładność głębi **1,48 ± 0,28 mm** (twarze zdrowe); optimum **1,07 mm przy 35 cm**; regresja dokładności względem dystansu: y = 0,003x + 0,1715 (r = 0,78) |
| Özsoy i in. [9], *J Craniofac Surg* 2026 | tani czujnik głębi | skaner światła strukturalnego + suwmiarka | **MAE 2,75 mm** (vs 1,64 mm dla światła strukturalnego); powtarzalność scan–rescan **0,84 mm** (vs 0,36 mm); ICC 0,88–0,93; 14 z 16 odległości przekroczyło tolerancję 2 mm |

### 6.2 Dwa wnioski, które muszą trafić do metodyki

**Wniosek 1 — zakres zastosowań.** Özsoy i in. [9] konkludują wprost, że tani czujnik głębi *„suits morphometric surveys, ranking, and within-subject monitoring, not high-fidelity reconstruction"*. To **definiuje realistyczny cel naszego systemu**: analiza porównawcza, rankingowanie i monitorowanie zmian u tej samej osoby — nie precyzyjna diagnostyka bezwzględna. Zapisanie tego w rozdziale o ograniczeniach systemu jest oznaką dojrzałości pracy, nie jej słabością.

**Wniosek 2 — nie raportować samego ICC.** Cytat z [9]: *„a high ICC alone does not establish clinical usability; absolute error must accompany it."* ICC = 0,93 przy MAE = 2,75 mm oznacza, że pomiary dobrze się rangują, ale bezwzględnie się mylą. **W walidacji (zadanie 7) trzeba raportować ICC + MAE + granice zgodności Blanda–Altmana + powtarzalność test–retest.** Sam ICC to typowy błąd raportowania w tego typu pracach.

### 6.3 Wymagania dla stanowiska — synteza literatury

Na podstawie [8], [9] i protokołów fotografii standaryzowanej (m.in. porównanie Frankfort Horizontal vs Natural Head Position):

| Parametr | Rekomendacja | Uzasadnienie |
|---|---|---|
| Dystans kamera–twarz | **stały, ok. 35–50 cm**, wymuszony fizycznie (podpórka/znacznik) | dokładność głębi degraduje się liniowo z dystansem [8] |
| Pozycja głowy | **Natural Head Position** z rejestracją lustra, opcjonalnie stabilizacja podbródkowa | NHP jest powtarzalna międzysesyjnie; Frankfort Horizontal zależy od landmarków, które sami estymujemy — ryzyko błędu okrężnego |
| Oświetlenie | dwa źródła rozproszone symetryczne, stała temperatura barwowa, brak okien | asymetryczne oświetlenie generuje pozorną asymetrię w kanale RGB i szum w mapie głębi |
| Tło | jednolite, matowe, kontrastowe wobec skóry | **patrz rozdz. 7.2 — kolor tła potrafi stać się nieświadomym predyktorem modelu** |
| Ekspresja | neutralna, usta zamknięte, oczy otwarte, bez okularów/biżuterii, włosy odsłaniające czoło i uszy | ekspresja zmienia geometrię o wartości przewyższające mierzoną asymetrię |
| Protokół | **min. 3 akwizycje na osobę** w jednej sesji + powtórna sesja dla podpróby | umożliwia policzenie powtarzalności scan–rescan, bez której walidacja jest niekompletna |
| Kalibracja | kalibracja wewnętrzna kamery + wzorzec o znanych wymiarach w każdej sesji | weryfikacja skali metrycznej |

---

## 7. Uczenie maszynowe w ocenie atrakcyjności

### 7.1 Nurt 2D: Facial Beauty Prediction (FBP)

Dominujący paradygmat: regresja oceny estetycznej z obrazu RGB, trenowana na zbiorze z uśrednionymi ocenami ludzkimi. Benchmarkiem jest **SCUT-FBP5500** [10] — 5500 twarzy frontalnych (2000 kobiet azjatyckich, 2000 mężczyzn azjatyckich, 750 kobiet i 750 mężczyzn rasy kaukaskiej), oceny 1–5 od 60 osób, **86 punktów charakterystycznych** dołączonych do zbioru, dwa protokoły ewaluacji (5-fold CV oraz podział 60/40). Metryki: Pearson Correlation (PC), MAE, RMSE.

Wyniki bazowe podane przez autorów zbioru [10] — to jest **punkt odniesienia, do którego należy porównywać własne rezultaty**:

| Model | 5-fold CV: PC / MAE / RMSE | Podział 60/40: PC / MAE / RMSE |
|---|---|---|
| AlexNet | 0,8634 / 0,2651 / 0,3481 | 0,8298 / 0,2938 / 0,3819 |
| ResNet-18 | 0,8900 / 0,2419 / 0,3166 | 0,8513 / 0,2818 / 0,3703 |
| ResNeXt-50 | **0,8997 / 0,2291 / 0,3017** | **0,8777 / 0,2518 / 0,3325** |

Czyli najlepszy model bazowy osiąga PC ≈ 0,90, co odpowiada R² ≈ 0,81 — na dużym, dobrze oznaczonym zbiorze.

### 7.2 Żejmo, Gielert, Grabski, Kostek (2023) — pozycja [11]

*(Politechnika Gdańska, Wydział ETI, Laboratorium Akustyki Fonicznej — praca z listy promotora)*

**Podejście:** ocena końcowa jako suma predykcji **trzech niezależnych modeli**:
1. model oparty na **dominujących kolorach tła** zdjęcia,
2. model oparty na wstępnie wytrenowanej głębokiej sieci neuronowej,
3. model oparty na **proporcjach twarzy** liczonych z odległości między punktami kluczowymi.

**Dane:** trening na SCUT-FBP5500, test na **Face Research Lab London Set** [12] — czyli **ewaluacja międzyzbiorowa** (cross-dataset), co jest mocną stroną tej pracy.

**Testowane algorytmy:** LinearSVR, SGDRegressor, Lasso, RandomForestRegressor oraz Xception, VGG19, ResNet50v2, MobileNetV2.

**Wyniki:** wykryto **systematyczne różnice błędu między bazami**, prawdopodobnie wynikające z odmiennego sposobu zbierania ocen. Brak jednoznacznie najlepszego algorytmu; najlepsze rezultaty uzyskano przy podaniu regresorowi **pięciu klastrów kolorystycznych**.

**Krytyczna obserwacja, którą warto rozwinąć w pracy.** To, że *kolor tła* okazał się użytecznym predyktorem estetyki twarzy, jest klasycznym przykładem **shortcut learning** — model wykorzystuje artefakt procesu zbierania danych (zdjęcia studyjne wyższej jakości mają inne tła i wyższe oceny), a nie cechę twarzy. Praca [11] uczciwie to raportuje i traktuje jako obserwację o zbiorach danych.

> **To jest bezpośrednie uzasadnienie zadania 2 naszej pracy.** Standaryzowane stanowisko akwizycyjne eliminuje właśnie tę klasę artefaktów: stałe tło, stałe oświetlenie, stały dystans. Można to jawnie postawić jako motywację: *„[11] pokazuje, że modele uczą się kontekstu zdjęcia; niniejsza praca kontroluje kontekst na poziomie akwizycji"*.

### 7.3 Moridani, Jamiee, Saghafi (2023) — pozycja [13]

**Podejście:** klasyczne uczenie maszynowe (k-najbliższych sąsiadów, Support Vector Regression) na cechach obejmujących **symetrię i proporcje** twarzy.

**Raportowane wyniki:** KNN — R² = 0,9902; RMSE = 0,0056; MAPE = 0,0856. Autorzy twierdzą, że współczynnik korelacji przewyższa zgodność ocen ludzkich.

**Ocena krytyczna — konieczna w przeglądzie.** R² = 0,99 w predykcji subiektywnej oceny estetycznej jest wartością **wyższą niż typowa zgodność między samymi oceniającymi ludźmi**. Dla porównania: najlepszy model bazowy na SCUT-FBP5500 osiąga PC = 0,8997 (R² ≈ 0,81) przy MAE = 0,2291 na skali 1–5 [10]. Wynik z [13] wymaga ostrożnej interpretacji; najbardziej prawdopodobne wyjaśnienia to niewielki zbiór danych, brak ścisłego rozdziału train/test na poziomie osób lub przeciek informacji przez etap selekcji cech. **Nie znaczy to, że praca jest bezwartościowa** — jest cenna jako przykład podejścia opartego na interpretowalnych cechach geometrycznych, ale jej wyników nie należy traktować jako punktu odniesienia do pobicia.

*(Rekomendacja: w pracy sformułować to dyplomatycznie — „wyniki uzyskane na ograniczonym zbiorze danych, wymagające potwierdzenia w protokole walidacji krzyżowej na poziomie osób".)*

### 7.4 Nurt 3D — najbliższy naszej pracy

**Beauty3DFaceNet** — Xiao, Wu, Wang, Yang, Jin [14] (*Computers & Graphics* 98, 2021, 11–18). Głęboka sieć predykująca atrakcyjność z **modeli 3D**, łącząca informację geometryczną (chmura punktów) i teksturalną, z modułem fuzji cech i próbkowaniem sterowanym landmarkami. Zbiór własny **ShadowFace3D** — 6000 modeli 3D z ocenami. Uzyskano istotną korelację ze średnimi ocenami ludzkimi. Kluczowa deklaracja autorów: metoda **nie wymaga ręcznie projektowanych cech**.

**Hu, Wang, Qu, Li** [15] (*Journal of Dentistry* 157, 2025, 105735). 1272 zdjęcia 3D pacjentów ortodontycznych (6–18 lat), oceny VAS od 7 ortodontów, porównanie 8 architektur CNN (ResNet18/50/101, VGG-16/19, Inception-v3, MobileNet-v2, DenseNet121). Najlepszy **DenseNet121** (dokładność predykcji i korelacja rangowa), ResNet18 najlepszy kompromis czas/jakość, MobileNet-v2 najsłabszy. **Uwaga metodyczna:** zdjęcia 3D konwertowano do 2D przed podaniem do sieci — czyli praca korzysta z akwizycji 3D, ale nie z geometrii 3D. To pozostawia przestrzeń dla podejścia faktycznie geometrycznego.

> **Luka widoczna gołym okiem:** [14] jest w pełni 3D, ale end-to-end i nieinterpretowalny; [15] jest interpretowalny w akwizycji, ale spłaszcza dane do 2D. **Brakuje pracy 3D, interpretowalnej, opartej na jawnych cechach geometrycznych** — i to jest nasza nisza (patrz rozdz. 12).

### 7.5 Modele wizyjno-językowe (VLM)

Roygaga i Bharati [16] (WACV 2026, s. 514–526) — praca z listy promotora. Badanie, w jakim stopniu modele wizyjno-językowe **internalizują i odtwarzają ludzkie uprzedzenia** przy ocenie subiektywnych atrybutów twarzy (np. wiarygodności).

Trzyetapowy pipeline: (1) ocena lokalizacji regionów — na czym VLM się skupia (brwi, oczy); (2) predykcja subiektywnych ocen porównywana z ocenami ludzkimi przez MAE; (3) analiza przestrzeni osadzeń z wprowadzeniem **Context-relevant Generated Captions (CGC)**.

Dane: Chicago Face Database (597 twarzy) [17], 10k US Adult Faces (2222), One Million Impressions (1004). Wyniki: CGC zwiększyły zgodność z ocenami ludzkimi (przykładowo o 33% względnie dla wiarygodności); LLaVA najlepszy spośród porównywanych VLM.

**Znaczenie dla pracy:** [16] to najnowszy punkt odniesienia i naturalny „przeciwnik" w części eksperymentalnej. Można postawić pytanie badawcze: *czy jawne cechy geometryczne z danych 3D wyjaśniają oceny estetyczne lepiej, gorzej, czy komplementarnie względem VLM działającego na obrazie RGB?* Odpowiedź w każdą stronę jest publikowalna.

---

## 8. Zbiory danych — zestawienie

| Zbiór | Rozmiar | Modalność | Oceny | Oceniający | Landmarki | Uwagi |
|---|---|---|---|---|---|---|
| **SCUT-FBP5500** [10] | 5500 | 2D RGB frontalne | 1–5 | 60 | 86 | Standard porównawczy FBP; nierównowaga etniczna (Azja ≫ Kaukaz) |
| **MEBeauty** [18] | 2550 | 2D „in the wild" | oceny generyczne i indywidualne | ok. 300 | — | 6 grup etnicznych; tylko cele niekomercyjne |
| **Face Research Lab London** [12] | 102 osoby | 2D, 1350×1350, wiele ujęć | 1–7 | **2513** | 189 (szablon) | Bardzo wysoka wiarygodność ocen; CC-BY; zbiór testowy w [11] |
| **Chicago Face Database** [17] | 597+ | 2D standaryzowane | wielowymiarowe normy | wiele | tak | Standaryzowana akwizycja, bogate metadane; użyty w [16] |
| **ShadowFace3D** [14] | 6000 | **modele 3D** | oceny ludzkie | — | tak | Nie znaleziono publicznego linku do pobrania — **do sprawdzenia** |
| **10k US Adult Faces** | 2222 | 2D | pamięciowość, atrybuty | wiele | — | Użyty w [16] |
| **One Million Impressions** | 1004 | 2D (generowane) | wrażenia społeczne | wiele | — | Twarze syntetyczne (GAN) |

**Obserwacja krytyczna:** publicznie dostępnych zbiorów **3D** z ocenami atrakcyjności praktycznie nie ma. To poważne ograniczenie dla zadania 7 (walidacja) i **argument za zbudowaniem własnego, choćby małego zbioru** na stanowisku z zadania 2 — nawet 60–100 osób z powtórzonymi sesjami ma wartość, jeśli akwizycja jest kontrolowana i protokół opisany.

---

## 9. Metryki ewaluacji

Standard w nurcie FBP: **Pearson Correlation (PC)**, **MAE**, **RMSE**; w pracach klinicznych dodatkowo **korelacja rangowa (Spearman)**.

Zalecenia dla naszej pracy, wynikające z przeglądu:

1. **Raportować PC/Spearman równolegle z MAE** — [9] pokazuje dlaczego (wysoka korelacja przy dużym błędzie bezwzględnym).
2. **Walidacja krzyżowa na poziomie osób**, nie zdjęć — inaczej te same twarze trafiają do train i test.
3. **Podać górną granicę osiągalną** — zgodność między oceniającymi (ICC oceniających, korelacja split-half). Model nie może sensownie przewyższyć wiarygodności etykiet; deklaracje typu [13] o „przewyższeniu ocen ludzkich" wymagają tego kontekstu.
4. **Ewaluacja międzyzbiorowa** — [11] pokazuje, że wyniki wewnątrz jednego zbioru są zawyżone.
5. **Zgłosić metryki uczciwości** — patrz rozdz. 10.
6. **Bland–Altman + powtarzalność test–retest** dla części pomiarowej (odległości, kąty, wskaźniki asymetrii).

---

## 10. Etyka, stronniczość modeli i dane osobowe

### 10.1 Stronniczość etniczna modeli oceniających urodę

Hamel i Busch [19] (arXiv:2509.24138, 2025) przetestowali dwa regresory ResNet-152 dostrojone odpowiednio na SCUT-FBP5500 i MEBeauty, walidując międzyzbiorowo na FairFace. Wyniki (testy Kruskala-Wallisa z post hoc Dunna):

- **istotne różnice predykcji między grupami etnicznymi (p < 0,001)** — również przy ocenie na zbiorach zrównoważonych,
- tylko **4,8–9,5%** porównań międzygrupowych spełniało kryterium parytetu rozkładów,
- obserwowana **amplifikacja** społecznych uprzedzeń estetycznych przez algorytm, nie ich redukcja,
- **zrównoważenie danych treningowych samo w sobie nie wystarcza** do usunięcia stronniczości.

### 10.2 Konsekwencje dla pracy

To nie jest opcjonalny akapit „o etyce" — to element metodyki, o który padnie pytanie na obronie:

1. **W rozdziale ewaluacji policzyć metryki uczciwości** (różnice MAE i rozkładów predykcji między podgrupami płci i, jeśli próba pozwoli, wieku).
2. **Jawnie ograniczyć deklarowane zastosowanie systemu** — wsparcie oceny estetycznej i analizy porównawczej (jak w celu pracy), a nie ocena wartości osoby.
3. **RODO:** obraz twarzy przetwarzany w celu jednoznacznej identyfikacji to dane biometryczne (art. 9 RODO, szczególna kategoria). Nawet jeśli nasz cel nie jest identyfikacyjny, wymagane są: świadoma zgoda pisemna uczestników, minimalizacja i pseudonimizacja danych, określony okres retencji, bezpieczne przechowywanie. **Sprawdzić, czy uczelnia wymaga zgody komisji etycznej** — jeśli tak, wniosek trzeba złożyć zanim rozpocznie się akwizycja (to zwykle 4–8 tygodni; łatwo tym zablokować cały harmonogram).
4. Rozważyć **wariant systemu działający wyłącznie na geometrii** (chmura punktów bez tekstury) — istotnie zmniejsza ryzyko związane z danymi osobowymi i jest mocnym argumentem projektowym.

---

## 11. Tabela porównawcza kluczowych prac

| # | Praca | Rok | Dane wejściowe | Cechy | Metoda | Zbiór | Wynik | Ograniczenie |
|---|---|---|---|---|---|---|---|---|
| [11] | Żejmo i in. | 2023 | 2D RGB | kolory tła + cechy DNN + proporcje z punktów | zespół 3 modeli; SVR/Lasso/RF + CNN | SCUT-FBP5500 → FRL London | brak jednoznacznego zwycięzcy; najlepiej z 5 klastrami koloru | predyktor kolorystyczny = artefakt zbioru; brak 3D |
| [13] | Moridani i in. | 2023 | 2D | symetria + proporcje | KNN, SVR | własny | R²=0,9902; RMSE=0,0056 | wynik nierealistycznie wysoki; brak opisu protokołu podziału danych |
| [16] | Roygaga & Bharati | 2026 | 2D RGB + tekst | osadzenia VLM, CGC | ocena VLM w 3 etapach | CFD, 10k US, 1M Impressions | +33% zgodności (wiarygodność); LLaVA najlepszy | atrybuty subiektywne inne niż atrakcyjność; brak geometrii |
| [14] | Xiao i in. (Beauty3DFaceNet) | 2021 | **3D + tekstura** | uczone (chmura punktów + tekstura) | CNN z fuzją cech | ShadowFace3D (6000) | istotna korelacja z ocenami | nieinterpretowalny; zbiór niedostępny publicznie |
| [15] | Hu i in. | 2025 | zdjęcia 3D → 2D | uczone | 8 architektur CNN | 1272 pacjentów ortod. | DenseNet121 najlepszy | geometria 3D niewykorzystana; wąska grupa wiekowa |
| [5] | Peng i in. (przegląd) | 2026 | skany 3D | — | przegląd 4 kategorii metod asymetrii | 14 prac | template-based preferowane | brak połączenia z oceną atrakcyjności |
| [4] | Zwahlen i in. | 2022 | zdjęcia 3D | 77 kanonów/kątów | korelacja z VAS | 30 twarzy, 163 sędziów | tylko ~14% parametrów istotnych | brak modelu predykcyjnego |
| [2] | Lee i in. | 2025 | 2D | asymetria, dystynktywność, dymorfizm | liniowe modele mieszane | 100 twarzy, 400 oceniających | **symetria nieistotna**; uśrednienie i kobiecość istotne | 2D; próba jednorodna kulturowo |

---

## 12. Luka badawcza i pozycjonowanie pracy

### 12.1 Co pokazuje przegląd

1. Nurt **FBP** jest dojrzały, ale niemal wyłącznie **2D** i **nieinterpretowalny** — modele end-to-end podające liczbę bez uzasadnienia ([11], [15]).
2. Nurt **analizy asymetrii 3D** jest metodycznie rozwinięty (4 kategorie metod [5]), ale **rozwijany osobno**, w kontekście klinicznym, **bez powiązania z percepcją atrakcyjności**.
3. **Kanony klasyczne są słabo wspierane empirycznie** ([3], [4]), a nawet symetria jako predyktor została podważona ([2]) — więc pole potrzebuje **pomiarów, nie założeń**.
4. **Brakuje publicznych zbiorów 3D z ocenami** — akwizycja własna ma realną wartość.
5. Tanie kamery głębi są **wystarczające do rankingowania i monitorowania**, ale **nie do rekonstrukcji wysokiej wierności** [9] — trzeba to zaprojektować, nie odkryć na końcu.

### 12.2 Sformułowanie luki

> Nie istnieje otwarty, zwalidowany system łączący **standaryzowaną akwizycję z taniej kamery głębi**, **jawne, interpretowalne cechy geometryczne 3D** (symetria rozdzielona na składową kierunkową i fluktuacyjną, proporcje, kąty) oraz **empiryczną weryfikację ich związku z percepcją atrakcyjności** — z raportowaniem zarówno dokładności bezwzględnej, jak i metryk uczciwości.

### 12.3 Proponowane pytania badawcze

- **PB1.** Jaka jest powtarzalność (test–retest) wskaźników symetrii i proporcji wyznaczanych z taniej kamery głębi na standaryzowanym stanowisku, i jak wypada względem dokładności raportowanej w [8] i [9]?
- **PB2.** Które z jawnych cech geometrycznych 3D (kanony, wskaźniki asymetrii, odległość Mahalanobisa od centroidu populacji) wyjaśniają wariancję ocen atrakcyjności, po wzajemnej kontroli?
- **PB3.** Czy — zgodnie z [2] — po kontroli uśrednienia symetria traci moc predykcyjną także na danych **3D**? *(w literaturze [2] testowano to na 2D — replikacja w 3D jest oryginalnym wkładem)*
- **PB4.** Jak model oparty na interpretowalnych cechach geometrycznych wypada względem modelu głębokiego i względem VLM ([16]) — pod kątem dokładności i pod kątem uczciwości między podgrupami?

### 12.4 Mapowanie zadań promotora na rozdziały

| Zadanie | Rozdział pracy | Kluczowe źródła |
|---|---|---|
| 1. Przegląd literatury | R2 | wszystkie |
| 2. Stanowisko akwizycyjne | R3 | [8], [9], rozdz. 6.3 |
| 3. Detekcja punktów (MediaPipe) | R4.1 | [6], [7] |
| 4. Ekstrakcja cech geometrycznych | R4.2 | [4], kanony Farkasa |
| 5. Algorytm symetrii i harmonii | R4.3 | [5], rozdz. 2.3–2.4 |
| 6. Integracja modeli AI | R4.4 | [10], [14], [15], [16] |
| 7. Walidacja | R5 | [9], [19], rozdz. 9 |

---

## 13. Do doczytania / zweryfikowania

- [ ] **Hammadi i in. 2022**, *Sensors* 22(18):6850 — porównanie MediaPipe / OpenPose / 3DDFA-V2 względem motion capture. Pozycja cytowana pośrednio; **pobrać oryginał i sprawdzić liczby**.
- [ ] **Grishchenko i in., Attention Mesh** (arXiv:2006.10962) — ulepszona wersja Face Mesh; zweryfikować dane bibliograficzne i czy jest to wersja obecna w aktualnym MediaPipe Face Landmarker.
- [ ] **Farkas L.G., *Anthropometry of the Head and Face*** — źródło kanoniczne definicji punktów antropometrycznych. Konieczne dla zadania 4; sprawdzić dostępność w bibliotece uczelnianej.
- [x] ~~Liang i in. 2018 (SCUT-FBP5500) — wyniki benchmarku~~ — **zrobione**, tabela w rozdz. 7.1 (preprint arXiv:1801.06345).
- [ ] **Dostępność ShadowFace3D** [14] — sprawdzić, czy zbiór jest udostępniany na wniosek (napisać do autorów; to może zaoszczędzić miesiące).
- [ ] **Przegląd FBP 2025** — *A comprehensive review of facial beauty prediction using deep learning techniques*, Engineering Applications of AI, doi do potwierdzenia (S0952197625020172); dostęp przez bibliotekę uczelnianą.
- [ ] **Przeglądy metod asymetrii cytowane w [5]** — rozwinąć 14 prac źródłowych dla rozdziału 4.
- [ ] **Regulacje uczelniane** — czy wymagana zgoda komisji etycznej na akwizycję wizerunków; wzór formularza zgody.
- [ ] **Specyfikacja sprzętu** — ustalić z katedrą dostępność RealSense D435/D455 lub Orbbec Femto; przy zakupie porównać z [8], [9] pod kątem realnego błędu.

---

## 14. Bibliografia

[1] Rhodes, G. (2006). The evolutionary psychology of facial beauty. *Annual Review of Psychology*, 57, 199–226. https://doi.org/10.1146/annurev.psych.57.102904.190208

[2] Lee, P., Li, J., Rafiee, Y., Jones, B.C., & Shiramizu, V.K.M. (2025). Further evidence that averageness and femininity, rather than symmetry and masculinity, predict facial attractiveness judgments. *Scientific Reports*, 15, 5498. https://doi.org/10.1038/s41598-025-86974-0

[3] Naini, F.B. (2024). The golden ratio — dispelling the myth. *Maxillofacial Plastic and Reconstructive Surgery*, 46, 2. https://doi.org/10.1186/s40902-024-00411-2

[4] Zwahlen, R.A., Tang, A.T.H., Leung, W.K., & Tan, S.K. (2022). Does 3-dimensional facial attractiveness relate to golden ratio, neoclassical canons, 'ideal' ratios and 'ideal' angles? *Maxillofacial Plastic and Reconstructive Surgery*, 44, 28. https://doi.org/10.1186/s40902-022-00358-2

[5] Peng, J., Qu, W., Zhang, S., & Lin, Y. (2026). Automated assessment of 3D facial asymmetry: a systematic review. *European Journal of Orthodontics*, 48(3), cjag012. https://doi.org/10.1093/ejo/cjag012

[6] Kartynnik, Y., Ablavatski, A., Grishchenko, I., & Grundmann, M. (2019). Real-time facial surface geometry from monocular video on mobile GPUs. *CVPR Workshop on Computer Vision for AR/VR*. arXiv:1907.06724

[7] Li, T., Bolkart, T., Black, M.J., Li, H., & Romero, J. (2017). Learning a model of facial shape and expression from 4D scans. *ACM Transactions on Graphics*, 36(6), 194. https://doi.org/10.1145/3130800.3130813

[8] ten Harkel, T.C., Speksnijder, C.M., van der Heijden, F., et al. (2017). Depth accuracy of the RealSense F200: Low-cost 4D facial imaging. *Scientific Reports*, 7, 16263. https://doi.org/10.1038/s41598-017-16608-7

[9] Özsoy, U., Alkan, E., Yıldırım, Y., & Yılmaz, B. (2026). Validating a low-cost depth sensor for facial anthropometry: capabilities and appropriate use. *Journal of Craniofacial Surgery*. https://doi.org/10.1097/SCS.0000000000013219

[10] Liang, L., Lin, L., Jin, L., Xie, D., & Li, M. (2018). SCUT-FBP5500: A diverse benchmark dataset for multi-paradigm facial beauty prediction. *24th International Conference on Pattern Recognition (ICPR)*. arXiv:1801.06345

[11] Żejmo, A., Gielert, M., Grabski, M., & Kostek, B. (2023). Assessing the attractiveness of human face based on machine learning. *Procedia Computer Science*, 225, 1019–1027. https://doi.org/10.1016/j.procs.2023.10.089

[12] DeBruine, L., & Jones, B. (2017). Face Research Lab London Set. *figshare*. https://doi.org/10.6084/m9.figshare.5047666

[13] Moridani, M.K., Jamiee, N., & Saghafi, S. (2023). Human-like evaluation by facial attractiveness intelligent machine. *International Journal of Cognitive Computing in Engineering*, 4, 160–169. https://doi.org/10.1016/j.ijcce.2023.04.001

[14] Xiao, Q., Wu, Y., Wang, D., Yang, Y.-L., & Jin, X. (2021). Beauty3DFaceNet: Deep geometry and texture fusion for 3D facial attractiveness prediction. *Computers & Graphics*, 98, 11–18. https://doi.org/10.1016/j.cag.2021.04.023

[15] Hu, J., Wang, C., Qu, Q., & Li, Q. (2025). Comparison of deep learning models for facial attractiveness assessment on 3D photos. *Journal of Dentistry*, 157, 105735. https://doi.org/10.1016/j.jdent.2025.105735

[16] Roygaga, C., & Bharati, A. (2026). Understanding human-like biases in VLMs via subjective face analytics. *Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)*, 514–526.

[17] Ma, D.S., Correll, J., & Wittenbrink, B. (2015). The Chicago Face Database: A free stimulus set of faces and norming data. *Behavior Research Methods*, 47(4), 1122–1135. https://doi.org/10.3758/s13428-014-0532-5

[18] Lebedeva, I., Guo, Y., & Ying, F. (2022). MEBeauty: a multi-ethnic facial beauty dataset in-the-wild. *Neural Computing and Applications*, 34, 14169–14183. https://doi.org/10.1007/s00521-021-06535-0

[19] Hamel, C., & Busch, M. (2025). Analysis of bias in deep learning facial beauty regressors. arXiv:2509.24138

---

*Wersja 1.0 — dokument roboczy. Pozycje oznaczone w rozdz. 13 wymagają weryfikacji w źródłach pełnotekstowych.*
