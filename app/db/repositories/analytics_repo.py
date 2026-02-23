from app.db.connection import get_db


def get_booked_calls_last_30_days() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM calls
            WHERE outcome = 'booked'
            AND created_at >= datetime('now', '-30 days')
        """).fetchall()
    return [dict(r) for r in rows]


def get_failed_calls_last_30_days() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM calls
            WHERE outcome IN ('negotiation_failed', 'dropped_call')
            AND created_at >= datetime('now', '-30 days')
        """).fetchall()
    return [dict(r) for r in rows]


def get_all_calls_last_30_days() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT c.*, bl.agreed_rate
            FROM calls c
            LEFT JOIN booked_loads bl ON c.call_id = bl.call_id
            WHERE c.created_at >= datetime('now', '-30 days')
        """).fetchall()
    return [dict(r) for r in rows]


def get_available_loads_by_equipment() -> dict[str, int]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT equipment_type, COUNT(*) as cnt
            FROM loads
            WHERE status = 'available'
            GROUP BY equipment_type
        """).fetchall()
    return {r["equipment_type"]: r["cnt"] for r in rows}


def get_recent_calls_by_equipment() -> dict[str, int]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT equipment_type, COUNT(*) as cnt
            FROM calls
            WHERE equipment_type IS NOT NULL
            AND created_at >= datetime('now', '-30 days')
            GROUP BY equipment_type
        """).fetchall()
    return {r["equipment_type"]: r["cnt"] for r in rows}
