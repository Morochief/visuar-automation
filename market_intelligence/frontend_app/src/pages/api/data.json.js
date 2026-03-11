import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';
import pg from 'pg';

const { Pool } = pg;

// ============================================
// AI-ENHANCED DATA ENDPOINT
// Uses Database (AI Mappings) + Rule-based fallback
// ============================================

// PostgreSQL connection - use localhost when running outside Docker
// In Docker, use 'postgres' hostname (via DATABASE_URL env var)
const DB_HOST = process.env.DATABASE_URL 
    ? new URL(process.env.DATABASE_URL).hostname 
    : (process.env.PGHOST || 'localhost');

const PG_CONFIG = process.env.DATABASE_URL 
    ? { connectionString: process.env.DATABASE_URL }
    : {
        host: DB_HOST,
        port: parseInt(process.env.PGPORT || '5432'),
        user: process.env.PGUSER || 'visuar_admin',
        password: process.env.PGPASSWORD || 'visuar_pass',
        database: process.env.PGDATABASE || 'market_intel_db'
      };

// Extrae todos los atributos de un producto desde su nombre
function extractAttributes(name, brand) {
    const n = name.toLowerCase();
    
    // 1. BTU - extraer capacidad
    let btu = null;
    const btuMatch = n.match(/(\d{1,2})\.?(?:000|0000)?\s*btu/i);
    if (btuMatch) {
        const val = parseInt(btuMatch[1]);
        if (val <= 60) btu = val * 1000;
        else btu = val;
    }
    
    // 2. Tipo de tecnología
    const isInverter = n.includes('inverter');
    
    // 3. Características adicionales
    const features = {
        wifi: n.includes('wifi') || n.includes('wi-fi'),
        cassette: n.includes('cassette'),
        pisoTecho: n.includes('piso') || n.includes('techo') || n.includes('pisotec'),
        ventana: n.includes('ventana'),
        portable: n.includes('portatil') || n.includes('portátil'),
        split: n.includes('split'),
        wall: n.includes('wall') || n.includes('pared'),
        ducto: n.includes('ducto'),
        gasEcologico: n.includes('gas ecol') || n.includes('ecolog'),
        conKit: n.includes('kit'),
        conSoporte: n.includes('soporte'),
        artcool: n.includes('artcool'),
        dualcool: n.includes('dualcool'),
        windfree: n.includes('windfree') || n.includes('wind-free'),
        round: n.includes('round'),
    };
    
    // Normalizar - si tiene ciertas features, es cierto
    features.cassette = features.cassette || n.includes('casette');
    features.pisoTecho = features.pisoTecho || n.includes('p/techo') || n.includes('p/techo');
    
    // 4. Extraer modelo/número de referencia
    const modelMatch = n.match(/(?:modelo|mod|mw|mr|gw|s4uw|s4nw|ar\d{2}|alt\d{2}|gw-\d{2})[a-z0-9]*/i);
    const model = modelMatch ? modelMatch[0].toUpperCase() : null;
    
    // 5. Normalizar Marca
    let realBrand = brand?.toUpperCase() || 'UNKNOWN';
    const knownBrands = ['SAMSUNG', 'LG', 'MIDEA', 'JAM', 'WHIRLPOOL', 'CARRIER', 'TOKYO', 'GOODWEATHER', 'HAUSTEC', 'OSTER', 'MIDAS', 'ALTECH', 'HISENSE', 'TCL'];
    
    // Si la marca es una palabra genérica, buscar en el título
    if (realBrand === 'AIRE' || realBrand === 'ACONDICIONADOR' || realBrand === 'UNKNOWN') {
        let foundBrand = 'UNKNOWN';
        for (const b of knownBrands) {
            if (n.includes(b.toLowerCase())) {
                foundBrand = b;
                break;
            }
        }
        realBrand = foundBrand;
    }
    
    return {
        btu,
        isInverter,
        features,
        model,
        brand: brand?.toUpperCase() || 'UNKNOWN',
        originalName: name
    };
}

// Calcula score de compatibilidad entre dos productos
function calculateMatchScore(attr1, attr2) {
    let score = 0;
    let maxScore = 0;
    const differences = [];
    
    // 0. BRAND CHECK - Si las marcas no coinciden, NO hacer match
    // Esto es CRÍTICO para evitar comparaciones inválidas (Haustec vs Goodweather)
    if (attr1.brand && attr2.brand && attr1.brand !== 'UNKNOWN' && attr2.brand !== 'UNKNOWN' && attr1.brand !== null && attr2.brand !== null) {
        if (attr1.brand !== attr2.brand) {
            // Marcas diferentes = no hay match válido
            return { score: 0, maxScore: 100, percentage: 0, differences: ['Marca diferente: ' + attr1.brand + ' vs ' + attr2.brand] };
        }
    }
    
    // 1. Marca (40 puntos)
    maxScore += 40;
    if (attr1.brand === attr2.brand) {
        score += 40;
    }
    
    // 2. BTU (30 puntos)
    maxScore += 30;
    if (attr1.btu && attr2.btu) {
        if (attr1.btu === attr2.btu) {
            score += 30;
        } else {
            const diff = Math.abs(attr1.btu - attr2.btu);
            if (diff <= 3000) score += 20;
            else if (diff <= 5000) score += 10;
            differences.push(`BTU: ${attr1.btu} vs ${attr2.btu}`);
        }
    }
    
    // 3. Tipo Inverter (20 puntos)
    maxScore += 20;
    if (attr1.isInverter === attr2.isInverter) {
        score += 20;
    } else {
        differences.push(attr1.isInverter ? 'Inverter vs ON/OFF' : 'ON/OFF vs Inverter');
    }
    
    // 4. Características (10 puntos)
    maxScore += 10;
    const feat1Keys = Object.keys(attr1.features).filter(k => attr1.features[k]);
    const feat2Keys = Object.keys(attr2.features).filter(k => attr2.features[k]);
    const commonFeats = feat1Keys.filter(f => attr2.features[f]);
    
    if (feat1Keys.length > 0 || feat2Keys.length > 0) {
        const featScore = (commonFeats.length * 2) / Math.max(feat1Keys.length, feat2Keys.length) * 10;
        score += Math.min(featScore, 10);
        
        feat1Keys.forEach(f => {
            if (!attr2.features[f]) {
                differences.push(f);
            }
        });
    }
    
    const percentage = Math.round((score / maxScore) * 100);
    
    return {
        score,
        maxScore,
        percentage,
        differences
    };
}

// Clasifica el nivel de match
function classifyMatch(matchResult, aiConfidence = null) {
    // If AI has matched this, use that confidence
    if (aiConfidence !== null) {
        if (aiConfidence >= 85) {
            return {
                level: 'EXACTO',
                label: 'AI Match',
                color: 'green',
                warning: null
            };
        } else if (aiConfidence >= 60) {
            return {
                level: 'PARCIAL',
                label: 'AI Match',
                color: 'yellow',
                warning: `AI Confidence: ${aiConfidence}%`
            };
        }
    }
    
    // Fall back to rule-based
    if (matchResult.percentage >= 85) {
        return {
            level: 'EXACTO',
            label: 'Match Exacto',
            color: 'green',
            warning: null
        };
    } else if (matchResult.percentage >= 60) {
        const diffs = matchResult.differences.slice(0, 3).join(', ');
        return {
            level: 'PARCIAL',
            label: 'Match Parcial',
            color: 'yellow',
            warning: `Diferencias: ${diffs}`
        };
    } else {
        return {
            level: 'NINGUNO',
            label: 'Sin Competidor',
            color: 'red',
            warning: 'No se encontró producto similar'
        };
    }
}

// Busca el mejor match en los productos de GG
function findBestMatch(vProduct, ggProducts, aiMappings = {}) {
    const vAttr = extractAttributes(vProduct.name, vProduct.brand);
    
    // Check if AI has already matched this product
    const aiMatch = aiMappings[vProduct.name];
    if (aiMatch) {
        // Find the matched GG product
        const matchedGG = ggProducts.find(g => g.name === aiMatch.ggName);
        if (matchedGG) {
            const gAttr = extractAttributes(matchedGG.name, matchedGG.brand);
            return {
                product: matchedGG,
                visuar: vProduct,
                visuarAttr: vAttr,
                ggAttr: gAttr,
                matchResult: { percentage: aiMatch.confidence },
                classification: classifyMatch({ percentage: aiMatch.confidence }, aiMatch.confidence),
                isAIMatch: true
            };
        }
    }
    
    let bestMatch = null;
    let bestResult = null;
    let bestPercentage = 0;
    
    for (const gg of ggProducts) {
        const ggAttr = extractAttributes(gg.name, gg.brand);
        const matchResult = calculateMatchScore(vAttr, ggAttr);
        
        if (matchResult && matchResult.percentage > bestPercentage) {
            bestPercentage = matchResult.percentage;
            bestMatch = gg;
            bestResult = matchResult;
        }
    }
    
    // If no match found, create a default result
    if (!bestResult) {
        bestResult = { percentage: 0, differences: ['Sin competidor'] };
    }
    
    const classification = classifyMatch(bestResult);
    
    return {
        product: bestMatch,
        visuar: vProduct,
        visuarAttr: vAttr,
        ggAttr: bestMatch ? extractAttributes(bestMatch.name, bestMatch.brand) : null,
        matchResult: bestResult,
        classification,
        isAIMatch: false
    };
}

// Load AI mappings from PostgreSQL database
async function loadAIMappings() {
    try {
        const pool = new Pool(PG_CONFIG);
        
        // Get mappings from pending_mappings (AI-generated)
        const query = `
            SELECT 
                p.name as visuar_name,
                cp.name as gg_name,
                pm.match_score as confidence
            FROM pending_mappings pm
            JOIN products p ON pm.suggested_product_id = p.id
            JOIN competitor_products cp ON pm.competitor_product_id = cp.id
        `;
        
        const result = await pool.query(query);
        await pool.end();
        
        // Create a lookup map
        const mappings = {};
        for (const row of result.rows) {
            mappings[row.visuar_name] = {
                ggName: row.gg_name,
                confidence: row.confidence
            };
        }
        console.log(`[DATA.API] Loaded ${Object.keys(mappings).length} AI mappings from PostgreSQL`);
        return mappings;
    } catch (err) {
        console.error("[DATA.API] Error loading AI mappings:", err.message);
        return {};
    }
}

// Astro API Endpoint
export async function GET() {
    try {
        const pool = new Pool(PG_CONFIG);
        
        // 1. Fetch Visuar Products (the base catalog)
        const visuarQuery = `
            SELECT p.id, p.name, p.brand, p.capacity_btu as btu, p.internal_cost,
                   cp.price, cp.scraped_at
            FROM products p
            JOIN competitor_products cp ON cp.product_id = p.id
            JOIN competitors c ON cp.competitor_id = c.id
            WHERE c.name = 'Visuar'
        `;
        const visuarResult = await pool.query(visuarQuery);
        const visuarProducts = visuarResult.rows;

        // 2. Load AI mappings
        const aiMappings = await loadAIMappings();

        // 3. Fetch GG products for comparison
        const ggQuery = `
            SELECT cp.id, cp.product_id, cp.name, cp.price, cp.raw_brand as brand, cp.scraped_at
            FROM competitor_products cp
            JOIN competitors c ON cp.competitor_id = c.id
            WHERE c.name = 'Gonzalez Gimenez'
        `;
        const ggResult = await pool.query(ggQuery);
        const ggProducts = ggResult.rows;

        await pool.end();

        console.log(`[DATA.API] Processing ${visuarProducts.length} Visuar products with ${Object.keys(aiMappings).length} AI mappings`);

        const rows = visuarProducts.map((vProduct, index) => {
            // Find match: prioritize direct product_id link, then AI suggestion
            let matchedProduct = ggProducts.find(g => g.product_id === vProduct.id);
            let isAIMatch = false;
            let confidence = matchedProduct ? 100 : 0;

            if (!matchedProduct) {
                const aiMatch = aiMappings[vProduct.name];
                if (aiMatch) {
                    matchedProduct = ggProducts.find(g => g.name === aiMatch.ggName);
                    isAIMatch = true;
                    confidence = aiMatch.confidence;
                }
            }

            // If still no match, try rule-based fallback
            let matchResult = { percentage: confidence };
            let classification;
            
            if (matchedProduct) {
                classification = classifyMatch({ percentage: confidence }, confidence);
            } else {
                const ruleMatch = findBestMatch(vProduct, ggProducts, aiMappings);
                matchedProduct = ruleMatch.product;
                classification = ruleMatch.classification;
                matchResult = ruleMatch.matchResult;
                isAIMatch = ruleMatch.isAIMatch;
            }

            const vPrice = parseFloat(vProduct.price);
            const gPrice = matchedProduct ? parseFloat(matchedProduct.price) : null;
            
            let diffPercent = null;
            let status = 'NO_COMPETITOR';
            
            if (gPrice !== null && vPrice > 0) {
                diffPercent = ((gPrice - vPrice) / vPrice) * 100;
                status = diffPercent > 0 ? 'WIN' : 'LOSS';
            }

            return {
                id: `visuar-${vProduct.id || index}`,
                name: vProduct.name,
                brand: vProduct.brand,
                btu: vProduct.btu,
                visuar_price: vPrice,
                gg_price: gPrice,
                gg_name: matchedProduct ? matchedProduct.name : null,
                diff_percent: diffPercent ? parseFloat(diffPercent.toFixed(2)) : null,
                status: status,
                match_level: classification.level,
                match_label: isAIMatch ? `🤖 ${classification.label}` : classification.label,
                match_color: isAIMatch ? 'emerald' : classification.color,
                is_ai_matched: isAIMatch,
                last_updated: vProduct.scraped_at || new Date().toISOString()
            };
        });
        
        // Ordenar: primero LOSS (somos más caros), luego EXACTO, luego SIN MATCH
        rows.sort((a, b) => {
            // Prioridad 1: LOSS primero (somos más caros - acción requerida)
            if (a.status === 'LOSS' && b.status !== 'LOSS') return -1;
            if (b.status === 'LOSS' && a.status !== 'LOSS') return 1;
            
            // Prioridad 2: Match EXACTO > PARCIAL > NINGUNO
            const levelOrder = { 'EXACTO': 3, 'PARCIAL': 2, 'NINGUN': 1 };
            const aLevel = levelOrder[a.match_level] || 0;
            const bLevel = levelOrder[b.match_level] || 0;
            if (aLevel !== bLevel) return bLevel - aLevel;
            
            // Prioridad 3: Por diferencia de precio (mayor diferencia primero)
            if (a.diff_percent !== null && b.diff_percent !== null) {
                return Math.abs(b.diff_percent) - Math.abs(a.diff_percent);
            }
            
            return 0;
        });
        
        // Generar estadísticas
        const stats = {
            total: rows.length,
            exact_match: rows.filter(r => r.match_level === 'EXACTO').length,
            partial_match: rows.filter(r => r.match_level === 'PARCIAL').length,
            no_match: rows.filter(r => r.match_level === 'NINGUN' || r.match_level === 'NINGUNO').length,
            wins: rows.filter(r => r.status === 'WIN').length,
            losses: rows.filter(r => r.status === 'LOSS').length,
            no_data: rows.filter(r => r.status === 'NO_COMPETITOR').length,
            ai_matched: rows.filter(r => r.is_ai_matched).length
        };
        
        console.log(`[DATA.API] Final stats:`, stats);
        
        return new Response(JSON.stringify({ rows, stats }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        });
    } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
    }
}
