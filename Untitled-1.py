# -*- coding: utf-8 -*- 

""" 

Consultar estado del familiar (CLI) 

----------------------------------- 

Lee la BD 'emociones.db' y permite: 

  - actual   : mostrar el registro más reciente de un adulto 

  - historial: listar registros en un rango (opcional) y exportar CSV 

Si se ejecuta SIN subcomandos, entra en modo rápido (te pregunta el adulto y muestra el último registro). 

 

Compatibilidad de esquema: 

  A) Dos tablas:  registro_emocional (adulto_id, fecha, turno, emocion_id, estado, comentario) 

                  emociones (id, nombre) 

  B) Una tabla :  registros (adulto, fecha, turno, emocion, estado, comentario) 

""" 

 

from __future__ import annotations 

import argparse, csv, sqlite3, sys 

from pathlib import Path 

from typing import Optional, List, Tuple 

 

DB_NAME = "emociones.db" 

 

# ---------------- Utilidades BD ---------------- 

 

def connect(db_path: Optional[Path] = None) -> sqlite3.Connection: 

    return sqlite3.connect(str(db_path or Path.cwd() / DB_NAME)) 

 

def has_table(conn: sqlite3.Connection, name: str) -> bool: 

    row = conn.execute( 

        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;", 

        (name,) 

    ).fetchone() 

    return bool(row) 

 

def detect_schema(conn: sqlite3.Connection) -> str: 

    if has_table(conn, "registro_emocional") and has_table(conn, "emociones"): 

        return "dos_tablas" 

    if has_table(conn, "registros"): 

        return "una_tabla" 

    raise RuntimeError( 

        "No se reconocen tablas. Esperaba (registro_emocional+emociones) o (registros)." 

    ) 

 

# ---------------- Consultas ---------------- 

 

def fetch_ultimo(conn: sqlite3.Connection, adulto: str) -> Optional[Tuple]: 

    """ 

    Devuelve tupla estándar: 

    (id, adulto, fecha, turno, emocion, estado, comentario) 

    """ 

    schema = detect_schema(conn) 

    if schema == "dos_tablas": 

        sql = """ 

        SELECT r.id, r.adulto_id, r.fecha, r.turno, e.nombre AS emocion, r.estado, r.comentario 

        FROM registro_emocional r 

        JOIN emociones e ON e.id = r.emocion_id 

        WHERE r.adulto_id = ? 

        ORDER BY r.fecha DESC, r.turno DESC, r.id DESC 

        LIMIT 1; 

        """ 

    else:  # una_tabla 

        sql = """ 

        SELECT id, adulto, fecha, turno, emocion, estado, comentario 

        FROM registros 

        WHERE adulto = ? 

        ORDER BY fecha DESC, turno DESC, id DESC 

        LIMIT 1; 

        """ 

    return conn.execute(sql, (adulto.strip(),)).fetchone() 

 

def fetch_historial(conn: sqlite3.Connection, adulto: str, 

                    desde: Optional[str], hasta: Optional[str], 

                    turno: Optional[str]) -> List[Tuple]: 

    """ 

    Devuelve lista de tuplas estándar: 

    (id, adulto, fecha, turno, emocion, estado, comentario) 

    """ 

    schema = detect_schema(conn) 

    clauses, params = ["adulto_id = ?" if schema == "dos_tablas" else "adulto = ?"], [adulto.strip()] 

    if desde: 

        clauses.append(("r.fecha >= ?" if schema == "dos_tablas" else "fecha >= ?")); params.append(desde) 

    if hasta: 

        clauses.append(("r.fecha <= ?" if schema == "dos_tablas" else "fecha <= ?")); params.append(hasta) 

    if turno: 

        clauses.append(("r.turno = ?" if schema == "dos_tablas" else "turno = ?")); params.append(turno.strip().upper()) 

 

    where = "WHERE " + " AND ".join(clauses) 

 

    if schema == "dos_tablas": 

        sql = f""" 

        SELECT r.id, r.adulto_id, r.fecha, r.turno, e.nombre AS emocion, r.estado, r.comentario 

        FROM registro_emocional r 

        JOIN emociones e ON e.id = r.emocion_id 

        {where} 

        ORDER BY r.fecha DESC, r.turno DESC, r.id DESC; 

        """ 

    else: 

        sql = f""" 

        SELECT id, adulto, fecha, turno, emocion, estado, comentario 

        FROM registros 

        {where} 

        ORDER BY fecha DESC, turno DESC, id DESC; 

        """ 

    return conn.execute(sql, params).fetchall() 

 

# ---------------- Presentación ---------------- 

 

def print_uno(row: Tuple) -> None: 

    if not row: 

        print("No hay registros para ese adulto.") 

        return 

    _id, adulto, fecha, turno, emocion, estado, cmt = row 

    print("\nÚltimo registro") 

    print("-" * 60) 

    print(f"ID:        { _id }") 

    print(f"Adulto:    { adulto }") 

    print(f"Fecha:     { fecha }   Turno: { turno }") 

    print(f"Emoción:   { emocion }   Estado: { estado }") 

    print(f"Comentario:{ ' ' + cmt if cmt else '' }") 

 

def print_tabla(rows: List[Tuple]) -> None: 

    if not rows: 

        print("No hay registros.") 

        return 

    print(f"{'ID':>3} {'Adulto':<10} {'Fecha':<10} {'Trn':<3} {'Emoción':<14} {'Est':<3}  Comentario") 

    print("-" * 90) 

    for _id, adulto, fecha, turno, emocion, estado, cmt in rows: 

        print(f"{_id:>3} {adulto:<10.10} {fecha:<10} {turno:<3} {emocion:<14.14} {estado:<3}  {cmt}") 

 

def export_csv(rows: List[Tuple], out: Path) -> Path: 

    with out.open("w", encoding="utf-8", newline="") as f: 

        w = csv.writer(f) 

        w.writerow(["id","adulto","fecha","turno","emocion","estado","comentario"]) 

        for r in rows: 

            w.writerow(r) 

    return out 

 

# ---------------- CLI ---------------- 

 

def build_parser() -> argparse.ArgumentParser: 

    p = argparse.ArgumentParser(description="Consultar estado del familiar") 

    p.add_argument("--db", type=Path, default=Path.cwd()/DB_NAME, help="ruta al .db (opcional)") 

    sub = p.add_subparsers(dest="cmd") 

 

    s1 = sub.add_parser("actual", help="muestra el último registro de un adulto") 

    s1.add_argument("--adulto", required=True) 

 

    s2 = sub.add_parser("historial", help="lista registros (filtros opcionales)") 

    s2.add_argument("--adulto", required=True) 

    s2.add_argument("--desde") 

    s2.add_argument("--hasta") 

    s2.add_argument("--turno", choices=["M","T"]) 

    s2.add_argument("--csv", type=Path, help="exportar a CSV") 

 

    sub.add_parser("menu", help="modo interactivo sencillo") 

    return p 

 

def run_menu(conn: sqlite3.Connection) -> None: 

    while True: 

        print("\n=== Consultar estado del familiar ===") 

        print("1) Último registro de un adulto") 

        print("2) Historial por adulto") 

        print("0) Salir") 

        op = input("Opción: ").strip() 

        if op == "0": 

            break 

        elif op == "1": 

            adulto = input("Adulto: ").strip() 

            print_uno(fetch_ultimo(conn, adulto)) 

        elif op == "2": 

            adulto = input("Adulto: ").strip() 

            desde  = (input("Desde (YYYY-MM-DD, vacío = sin filtro): ").strip() or None) 

            hasta  = (input("Hasta (YYYY-MM-DD, vacío = sin filtro): ").strip() or None) 

            turno  = (input("Turno (M/T, vacío = ambos): ").strip().upper() or None) 

            rows = fetch_historial(conn, adulto, desde, hasta, turno) 

            print_tabla(rows) 

        else: 

            print("Opción inválida.") 

 

def main(argv: Optional[list] = None) -> int: 

    args = build_parser().parse_args(argv) 

    conn = connect(args.db) 

 

    try: 

        # Modo rápido si no se pasa subcomando: pedir adulto y mostrar último 

        if args.cmd is None: 

            adulto = input("Adulto: ").strip() 

            print_uno(fetch_ultimo(conn, adulto)) 

            return 0 

 

        if args.cmd == "menu": 

            run_menu(conn); return 0 

 

        if args.cmd == "actual": 

            print_uno(fetch_ultimo(conn, args.adulto)); return 0 

 

        if args.cmd == "historial": 

            rows = fetch_historial(conn, args.adulto, args.desde, args.hasta, args.turno) 

            if args.csv: 

                out = export_csv(rows, args.csv) 

                print(f"✅ CSV exportado: {out.resolve()}") 

            else: 

                print_tabla(rows) 

            return 0 

 

        return 0 

    except Exception as e: 

        print(f"⚠️ Error: {e}") 

        return 1 

 

if __name__ == "__main__": 

    raise SystemExit(main()) 

 