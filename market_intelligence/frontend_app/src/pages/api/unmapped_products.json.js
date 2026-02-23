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

        // Query CompetitorProducts that are NOT mapped to any Canonical Product
        // AND are NOT waiting in the Pending Mappings queue
        const query = `
            SELECT 
                cp.id,
                cp.name,
                c.name as competitor_name
            FROM competitor_products cp
            JOIN competitors c ON cp.competitor_id = c.id
            LEFT JOIN pending_mappings pm ON cp.id = pm.competitor_product_id
            WHERE cp.product_id IS NULL 
              AND pm.id IS NULL
            ORDER BY c.name, cp.name;
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
