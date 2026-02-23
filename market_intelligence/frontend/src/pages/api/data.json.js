import sqlite3 from 'sqlite3';
import { resolve } from 'path';

// Astro API Endpoint that serves the SQLite view directly to React
export async function GET() {
    const dbPath = resolve('../backend/market_intel.db');

    return new Promise((resolveResponse) => {
        const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
            if (err) {
                resolveResponse(new Response(JSON.stringify({ error: "Failed to connect to database", details: err.message }), {
                    status: 500,
                    headers: { "Content-Type": "application/json" }
                }));
                return;
            }
        });

        const query = `
      SELECT 
        product_id as id,
        name,
        brand,
        visuar_price,
        bristol_price,
        diff_percent,
        status,
        last_updated
      FROM opportunity_margin_vw
      ORDER BY diff_percent DESC;
    `;

        db.all(query, [], (err, rows) => {
            db.close();

            if (err) {
                resolveResponse(new Response(JSON.stringify({ error: err.message }), {
                    status: 500,
                    headers: { "Content-Type": "application/json" }
                }));
                return;
            }

            resolveResponse(new Response(JSON.stringify(rows), {
                status: 200,
                headers: { "Content-Type": "application/json" }
            }));
        });
    });
}
