"""
generar_caliente.py
Sistema de Números Calientes
Calibrado con data real: Mar 1 - Jun 2, 2026 (703 sorteos)

Lógica:
  - hot_pos[:5] siempre (core)
  - +1 posición si signal > SIGNAL_MEDIAN (0.003)
  - Máx 6 números por draw
  - Sin topq como relleno
  - Sin ok_alert/a11 bonus (no respaldado por data)
"""

import json
import argparse
import ast
from datetime import datetime

# ─── DRAW PROFILES ────────────────────────────────────────────────────────────
# Calibrados con 703 sorteos (Mar 1 - Jun 2, 2026)
# hot_pos: posiciones 1-indexadas ordenadas por frecuencia de acierto histórico
# hit_rate: % de sorteos donde al menos un número del top12 cayó en resultado

DRAW_PROFILES = {
    "Anguila 10AM": {
        "hot_pos":  [5, 6, 4, 7, 1, 10, 2, 8, 12, 3],
        "hit_rate": 33.9,
        "sorteos":  56,
    },
    "Anguila 1PM": {
        "hot_pos":  [7, 11, 2, 12, 3, 6, 10, 1, 8, 4, 9, 5],
        "hit_rate": 31.7,
        "sorteos":  63,
    },
    "Anguila 6PM": {
        "hot_pos":  [2, 1, 7, 12, 5, 11, 8, 3, 6, 4, 9],
        "hit_rate": 33.8,
        "sorteos":  77,
    },
    "Anguila 9PM": {
        "hot_pos":  [3, 8, 6, 10, 9, 11, 1, 12, 5, 4, 2],
        "hit_rate": 31.2,
        "sorteos":  80,
    },
    "Loteria Nacional- Gana Más": {
        "hot_pos":  [4, 6, 5, 1, 11, 12, 3, 9, 7, 2, 10],
        "hit_rate": 31.4,
        "sorteos":  86,
    },
    "Loteria Nacional- Noche": {
        "hot_pos":  [8, 3, 11, 10, 6, 1, 7, 5, 12, 2],
        "hit_rate": 26.5,
        "sorteos":  83,
    },
    "Quiniela La Primera": {
        "hot_pos":  [8, 11, 7, 1, 9, 6, 4, 10, 3, 12, 5],
        "hit_rate": 26.2,
        "sorteos":  65,
    },
    "Quiniela La Primera Noche": {
        "hot_pos":  [5, 10, 12, 11, 3, 4, 9, 1, 8, 2, 6, 7],
        "hit_rate": 27.7,
        "sorteos":  65,
    },
    "Quiniela La Suerte": {
        "hot_pos":  [12, 10, 9, 2, 8, 6, 11, 7, 1, 4],
        "hit_rate": 27.5,
        "sorteos":  51,
    },
    "Quiniela La Suerte 6PM": {
        "hot_pos":  [12, 7, 4, 9, 6, 10, 8, 11, 3, 2],
        "hit_rate": 33.8,
        "sorteos":  77,
    },
}

# Señal mediana real de la data (percentil 50)
# Por encima → activa +1 posición extra
SIGNAL_MEDIAN = 0.003

# Draws con hit rate bajo — se incluyen pero con advertencia
WEAK_DRAWS = {"Quiniela La Primera", "Loteria Nacional- Noche"}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def parse_list(value):
    """Parsea top12/topq que pueden venir como string o lista."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return ast.literal_eval(value)
        except Exception:
            return []
    return []


def procesar_pick(pick: dict) -> dict | None:
    """
    Genera el bloque caliente para un pick individual.

    Parámetros esperados en pick:
      draw        str   nombre del draw (debe existir en DRAW_PROFILES)
      lottery     str   nombre de la lotería
      top12       list  los 12 números ordenados por el sistema principal
      best_signal float señal del sistema
      best_a11    int   valor a11
      ok_alert    bool  alerta ok
      date        str   fecha del sorteo (opcional)

    Retorna dict con la selección caliente, o None si el draw no existe.
    """
    draw = pick.get("draw", "")
    profile = DRAW_PROFILES.get(draw)

    if not profile:
        return None

    top12 = [str(n).zfill(2) for n in parse_list(pick.get("top12", []))]
    if len(top12) < 5:
        return None

    signal = float(pick.get("best_signal", 0))
    hot_pos = profile["hot_pos"]

    # Core: siempre las 5 posiciones más calientes
    n_pos = 5

    # Bonus: +1 si signal supera la mediana
    bonus_signal = signal > SIGNAL_MEDIAN
    if bonus_signal and len(hot_pos) > 5:
        n_pos = 6

    selected_pos = hot_pos[:n_pos]

    # Extraer números por posición (1-indexed), sin duplicados
    numeros = []
    for p in selected_pos:
        idx = p - 1
        if 0 <= idx < len(top12):
            num = top12[idx]
            if num not in numeros:
                numeros.append(num)

    # Clasificar calidad del draw
    hr = profile["hit_rate"]
    if hr >= 32:
        calidad = "fuerte"
    elif hr >= 28:
        calidad = "normal"
    else:
        calidad = "debil"

    return {
        "draw":               draw,
        "lottery":            pick.get("lottery", ""),
        "date":               pick.get("date", ""),
        "numeros":            numeros,
        "posiciones_usadas":  selected_pos,
        "n_numeros":          len(numeros),
        "bonus_signal":       bonus_signal,
        "signal":             round(signal, 6),
        "a11":                pick.get("best_a11", 0),
        "ok_alert":           pick.get("ok_alert", False),
        "hit_rate_historico": hr,
        "calidad_draw":       calidad,
        "advertencia":        "draw con HR bajo (<28%)" if draw in WEAK_DRAWS else None,
    }


# ─── MODOS DE USO ─────────────────────────────────────────────────────────────

def run(picks: list[dict], output_path: str = "caliente.json") -> dict:
    """
    Modo importado desde runner.py.

    picks: lista de dicts con los campos descritos en procesar_pick()
    output_path: ruta donde guardar el caliente.json

    Retorna el dict completo del caliente.json
    """
    loterias = {}
    skipped = []

    for pick in picks:
        resultado = procesar_pick(pick)
        if resultado is None:
            skipped.append(pick.get("draw", "?"))
            continue
        draw = resultado["draw"]
        loterias[draw] = resultado

    output = {
        "generado_en":    datetime.now().isoformat(timespec="seconds"),
        "calibrado_con":  "Mar 1 - Jun 2, 2026 (703 sorteos)",
        "signal_median":  SIGNAL_MEDIAN,
        "total_loterias": len(loterias),
        "skipped":        skipped,
        "loterias":       loterias,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[caliente] {len(loterias)} loterias → {output_path}")
    for draw, r in loterias.items():
        bonus = "  +signal" if r["bonus_signal"] else ""
        warn  = f"  ⚠ {r['advertencia']}" if r["advertencia"] else ""
        print(f"  {draw}: {r['numeros']} ({r['n_numeros']} nums){bonus}{warn}")

    return output


def run_from_json(input_path: str, output_path: str = "caliente.json") -> dict:
    """
    Modo línea de comandos: lee picks desde un JSON generado por el sistema principal.

    El JSON de entrada puede ser:
      - Una lista de picks directamente: [ {pick}, {pick}, ... ]
      - Un dict con clave 'picks' o 'loterias': { "picks": [...] }
    """
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        picks = data
    elif isinstance(data, dict):
        picks = data.get("picks") or data.get("loterias") or list(data.values())
    else:
        raise ValueError(f"Formato de entrada no reconocido: {type(data)}")

    return run(picks=picks, output_path=output_path)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Genera caliente.json con los números más probables por lotería."
    )
    parser.add_argument(
        "--input",  "-i",
        required=True,
        help="JSON con los picks activos generados por el sistema principal"
    )
    parser.add_argument(
        "--output", "-o",
        default="caliente.json",
        help="Ruta de salida (default: caliente.json)"
    )
    args = parser.parse_args()

    result = run_from_json(input_path=args.input, output_path=args.output)

    print(f"\nTotal loterias procesadas : {result['total_loterias']}")
    if result["skipped"]:
        print(f"Draws sin perfil (omitidos): {result['skipped']}")


if __name__ == "__main__":
    main()
