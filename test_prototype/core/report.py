"""Raporty HTML (jeden na ujęcie + strona zbiorcza) i tabele CSV z najważniejszymi wynikami."""
from __future__ import annotations

import csv
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"),
                   autoescape=select_autoescape(["html", "j2"]), trim_blocks=True, lstrip_blocks=True)


def _num(value, digits: int = 1, sign: bool = False) -> str:
    if value is None:
        return "—"
    text = f"{value:+.{digits}f}" if sign else f"{value:.{digits}f}"
    return text.replace(".", ",").replace("-", "−")


_env.filters["num"] = _num
_env.filters["status_icon"] = lambda s: {"ok": "✔", "błąd": "✘", "info": "ℹ"}.get(s, "?")


def _find(rows: list[dict], key: str, value: str) -> dict:
    return next((r for r in rows if r.get(key) == value), {})


def summary_row(r: dict) -> dict:
    """Najważniejsze liczby jednego wyniku (do tabeli zbiorczej i CSV)."""
    qc = r.get("kontrola_jakosci", {})
    errors = [c["warunek"] for c in qc.get("checks", []) if c["status"] == "błąd"]
    row = {"id": r["id"], "typ": r["typ"], "folder": r["folder"], "qc_ok": qc.get("ok", False),
           "qc_bledy": "; ".join(errors)}
    if r["typ"] == "2D" and "symetria" in r:
        s = r["symetria"]
        row.update({
            "asym_rms_proc_ipd": s["globalna"]["rms"]["proc_ipd"],
            "asym_rms_mm_orient": s["globalna"]["rms"]["mm"],
            "procrustes": s["globalna"]["procrustes"],
            "broda_mm_orient": _find(s["srodkowe"], "punkt", "gn").get("mm"),
            "kaciki_ust_pion_mm_orient": _find(s["pary"], "para", "ch")["pionowa"]["mm"],
            "yaw_deg": qc["poza"]["pnp_stabilne"]["yaw"],
        })
    if r["typ"] == "3D" and "symetria_powierzchnia" in r:
        s, p = r["symetria_powierzchnia"], r["symetria_punkty"]
        row.update({
            "pow_rms_mm": s["rms_mm"], "pow_rms_wygl_mm": s["wygladzone"]["rms_mm"],
            "pow_p95_wygl_mm": s["wygladzone"]["p95_abs_mm"],
            "broda_od_plaszczyzny_mm": _find(s["srodkowe_od_plaszczyzny"], "punkt", "gn").get("mm"),
            "pkt_rms_mm": p["globalna"]["rms"]["mm"],
            "kaciki_ust_pion_mm": _find(p["pary"], "para", "ch")["pionowa"]["mm"],
            "yaw3d_deg": qc["poza"]["z_punktow_3d"]["yaw"],
            "skala_teczowki_ipd_proc": _find(r["skala_teczowka_vs_glebia"], "nazwa", "ipd").get("roznica_proc"),
        })
    return row


def write_report(result: dict, out_dir: Path) -> Path:
    path = Path(out_dir) / "raport.html"
    path.write_text(_env.get_template("raport.html.j2").render(r=result))
    return path


def write_index(results: list[dict], out_root: Path, title: str) -> Path:
    out_root = Path(out_root)
    rows = [summary_row(r) for r in results]
    for typ in ("2D", "3D"):
        part = [row for row in rows if row["typ"] == typ]
        if part:
            keys = list(dict.fromkeys(k for row in part for k in row))
            with open(out_root / f"wyniki_{typ}.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys, delimiter=";")
                writer.writeheader()
                writer.writerows(part)
    by_id = {}
    for row in rows:
        by_id.setdefault(row["id"], {})[row["typ"]] = row
    pairs = [(i, v["2D"], v["3D"]) for i, v in by_id.items() if "2D" in v and "3D" in v]
    path = out_root / "index.html"
    path.write_text(_env.get_template("indeks.html.j2").render(
        title=title, rows=rows, pairs=pairs, results=results))
    return path
