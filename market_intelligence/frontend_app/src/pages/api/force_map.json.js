import sqlite3 from 'sqlite3';
import { resolve } from 'path';

export async function POST({ request }) {
    const dbPath = resolve('../backend/market_intel.db');
    let body;
    try {
        body = await request.json();
    } catch (e) {
        console.error("Error parsing JSON:", e);
        return new Response(JSON.stringify({ error: "Invalid JSON body", details: e.message }), { status: 400 });
    }

    const { competitor_product_id, canonical_product_id } = body;

    if (!competitor_product_id || !canonical_product_id) {
        return new Response(JSON.stringify({ error: "Missing competitor_product_id or canonical_product_id" }), { status: 400 });
    }

    return new Promise((resolveResponse) => {
        const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READWRITE, (err) => {
            if (err) {
                resolveResponse(new Response(JSON.stringify({ error: err.message }), { status: 500 }));
                return;
            }
        });

        db.serialize(() => {
            db.run('BEGIN TRANSACTION');

            // 1. Force the Link
            db.run(
                `UPDATE competitor_products SET product_id = ? WHERE id = ?`,
                [canonical_product_id, competitor_product_id],
                function (err) {
                    if (err) {
                        db.run('ROLLBACK');
                        db.close();
                        resolveResponse(new Response(JSON.stringify({ error: err.message }), { status: 500 }));
                        return;
                    }
                }
            );

            // 2. Remove any lingering suggestions just in case the AI generated one but the user ignored the Inbox
            db.run(
                `DELETE FROM pending_mappings WHERE competitor_product_id = ?`,
                [competitor_product_id],
                function (err) {
                    if (err) {
                        db.run('ROLLBACK');
                        db.close();
                        resolveResponse(new Response(JSON.stringify({ error: err.message }), { status: 500 }));
                        return;
                    }

                    db.run('COMMIT');
                    db.close();
                    resolveResponse(new Response(JSON.stringify({ success: true }), { status: 200 }));
                }
            );
        });
    });
}
