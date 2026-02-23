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

        // Query to get pending mappings with readable Context
        const query = `
            SELECT 
                pm.id as mapping_id,
                cp.id as raw_id,
                cp.name as raw_name,
                c.name as competitor_name,
                p.id as suggested_canonical_id,
                p.name as suggested_canonical_name,
                pm.match_score
            FROM pending_mappings pm
            JOIN competitor_products cp ON pm.competitor_product_id = cp.id
            JOIN competitors c ON cp.competitor_id = c.id
            JOIN products p ON pm.suggested_product_id = p.id
            WHERE pm.is_approved IS NULL
            ORDER BY pm.match_score DESC;
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
