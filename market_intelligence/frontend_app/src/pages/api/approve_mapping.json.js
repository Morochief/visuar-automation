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

    const { mapping_id, action } = body;

    if (!mapping_id || !['approve', 'reject'].includes(action)) {
        console.error("Invalid Payload:", { mapping_id, action });
        return new Response(JSON.stringify({ error: "Missing or invalid mapping_id / action", received: { mapping_id, action } }), { status: 400 });
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

            const isApproved = action === 'approve' ? 1 : 0;

            // 1. Update the Pending Mapping status
            db.run(
                `UPDATE pending_mappings SET is_approved = ? WHERE id = ?`,
                [isApproved, mapping_id],
                function (err) {
                    if (err) {
                        db.run('ROLLBACK');
                        db.close();
                        resolveResponse(new Response(JSON.stringify({ error: err.message }), { status: 500 }));
                        return;
                    }
                }
            );

            // 2. If approved, link the competitor product to the canonical product
            if (action === 'approve') {
                db.get(`SELECT competitor_product_id, suggested_product_id FROM pending_mappings WHERE id = ?`, [mapping_id], (err, row) => {
                    if (err || !row) {
                        db.run('ROLLBACK');
                        db.close();
                        resolveResponse(new Response(JSON.stringify({ error: "Mapping not found" }), { status: 404 }));
                        return;
                    }

                    db.run(
                        `UPDATE competitor_products SET product_id = ? WHERE id = ?`,
                        [row.suggested_product_id, row.competitor_product_id],
                        function (updateErr) {
                            if (updateErr) {
                                db.run('ROLLBACK');
                                db.close();
                                resolveResponse(new Response(JSON.stringify({ error: updateErr.message }), { status: 500 }));
                                return;
                            }
                            db.run('COMMIT');
                            db.close();
                            resolveResponse(new Response(JSON.stringify({ success: true }), { status: 200 }));
                        }
                    );
                });
            } else {
                db.run('COMMIT');
                db.close();
                resolveResponse(new Response(JSON.stringify({ success: true }), { status: 200 }));
            }
        });
    });
}
