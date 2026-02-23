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
                cp.id, 
                cp.name, 
                c.name as comp_name,
                (SELECT price FROM price_logs pl WHERE pl.competitor_product_id = cp.id ORDER BY scraped_at DESC LIMIT 1) as latest_price
            FROM competitor_products cp
            JOIN competitors c ON c.id = cp.competitor_id
            ORDER BY c.name, cp.name;
        `;

        db.all(query, [], (err, rows) => {
            db.close();
            if (err) {
                resolveResponse(new Response(JSON.stringify({ error: err.message }), { status: 500 }));
                return;
            }

            const visuar = rows.filter(r => r.comp_name.toLowerCase() === 'visuar' && r.latest_price != null);
            const competitors = rows.filter(r => r.comp_name.toLowerCase() !== 'visuar' && r.latest_price != null);

            resolveResponse(new Response(JSON.stringify({ visuar, competitors }), { status: 200 }));
        });
    });
}
