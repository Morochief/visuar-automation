import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

export async function GET() {
    try {
        const visuarPath = resolve('./public/api/visuar_ac_data.json');
        const ggPath = resolve('./public/api/gg_ac_data.json');
        
        let visuar = [];
        let gg = [];
        
        if (existsSync(visuarPath)) {
            const visuarData = JSON.parse(readFileSync(visuarPath, 'utf-8'));
            // Flatten the brand-organized structure
            visuar = Object.entries(visuarData).flatMap(([brand, products]) => 
                products.map(p => ({
                    ...p,
                    brand,
                    source: 'visuar'
                }))
            );
        }
        
        if (existsSync(ggPath)) {
            const ggData = JSON.parse(readFileSync(ggPath, 'utf-8'));
            gg = Object.entries(ggData).flatMap(([brand, products]) => 
                products.map(p => ({
                    ...p,
                    brand,
                    source: 'gg'
                }))
            );
        }
        
        return new Response(JSON.stringify({ visuar, gg }), { 
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        });
    } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
    }
}
