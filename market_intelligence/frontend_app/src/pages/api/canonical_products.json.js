import sqlite3 from 'sqlite3';
import { resolve } from 'path';

export async function GET() {
    const dbPath = resolve('../backend/market_intel.db');

    return new Promise((resolveResponse) => {
        const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
            if (err) {
                resolveResponse(new Response(JSON.stringify({ error: err.message }), { status: 500 }));
                return;
            }
        });

        const query = `
            SELECT 
                id,
                name,
                capacity_btu,
                is_inverter
            FROM products
            ORDER BY capacity_btu, name;
        `;

        db.all(query, [], (err, rows) => {
            db.close();
            if (err) {
                resolveResponse(new Response(JSON.stringify({ error: err.message }), { status: 500 }));
                return;
            }
            resolveResponse(new Response(JSON.stringify(rows), { status: 200 }));
        });
    });
}
