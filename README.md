# Facial-Analysis-MEng

System do standaryzowanej analizy symetrii, harmonii i percepcji atrakcyjności twarzy na podstawie danych 3D (praca magisterska).

## Struktura

```
src/facial3d/        pakiet: wczytywanie skanów, render, punkty MediaPipe, symetria, proporcje, wizualizacja
scripts/             skrypty analiz (analyze_scan.py — analiza pojedynczego skanu)
data/                dane twarzy — NIE są wersjonowane (licencje + RODO)
models/              modele MediaPipe — pobierane lokalnie, niewersjonowane
outputs/             wyniki generowane przez skrypty — niewersjonowane
```

## Uruchomienie

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

Pliki pobierane ręcznie (niewersjonowane):

- `models/face_landmarker.task` — https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
- `models/canonical_face_model.obj` — https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model.obj
- przykładowy skan: `data/raw/lee_perry_smith/` — pliki `LeePerrySmith.glb` i `Map-COL.jpg` z https://github.com/mrdoob/three.js/tree/dev/examples/models/gltf/LeePerrySmith

```bash
python scripts/analyze_scan.py
```

## Dane i atrybucja

Przykładowy skan: *Infinite, 3D Head Scan* — Lee Perry-Smith (Infinite-Realities), licencja CC BY 3.0.
