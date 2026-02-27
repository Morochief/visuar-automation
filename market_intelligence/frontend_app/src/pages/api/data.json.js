import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

// ============================================
// SISTEMA DE MATCHING INTELIGENTE POR ATRIBUTOS
// ============================================

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
    
    return {
        btu,
        isInverter,
        features,
        model,
        brand: brand?.toUpperCase() || 'UNKNOWN',
        originalName: name
    };
}

// Calculascore de compatibilidad entre dos productos
function calculateMatchScore(attr1, attr2) {
    let score = 0;
    let maxScore = 0;
    const differences = [];
    
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
            if (diff <= 3000) score += 20; // BTU similar
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
        
        // Agregar diferencias en features
        feat1Keys.forEach(f => {
            if (!attr2.features[f]) {
                differences.push(f);
            }
        });
    }
    
    // Calcular porcentaje
    const percentage = Math.round((score / maxScore) * 100);
    
    return {
        score,
        maxScore,
        percentage,
        differences
    };
}

// Clasifica el nivel de match
function classifyMatch(matchResult) {
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
function findBestMatch(vProduct, ggProducts) {
    const vAttr = extractAttributes(vProduct.name, vProduct.brand);
    
    let bestMatch = null;
    let bestResult = null;
    let bestPercentage = 0;
    
    for (const gg of ggProducts) {
        const ggAttr = extractAttributes(gg.name, gg.brand);
        const matchResult = calculateMatchScore(vAttr, ggAttr);
        
        if (matchResult.percentage > bestPercentage) {
            bestPercentage = matchResult.percentage;
            bestMatch = gg;
            bestResult = matchResult;
        }
    }
    
    const classification = classifyMatch(bestResult);
    
    return {
        product: bestMatch,
        visuar: vProduct,
        visuarAttr: vAttr,
        ggAttr: bestMatch ? extractAttributes(bestMatch.name, bestMatch.brand) : null,
        matchResult: bestResult,
        classification
    };
}

// Astro API Endpoint
export async function GET() {
    try {
        const visuarPath = resolve('./public/api/visuar_ac_data.json');
        const ggPath = resolve('./public/api/gg_ac_data.json');
        
        let visuar = [];
        let gg = [];
        
        if (existsSync(visuarPath)) {
            const visuarData = JSON.parse(readFileSync(visuarPath, 'utf-8'));
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
        
        // Filtrar solo aires acondicionados (eliminar cortinas de aire)
        gg = gg.filter(p => {
            const n = p.name.toLowerCase();
            return !n.includes('cortina');
        });
        
        // Procesar cada producto de Visuar y encontrar mejor match en GG
        const rows = visuar.map((vProduct, index) => {
            const match = findBestMatch(vProduct, gg);
            
            const vPrice = vProduct.price;
            const gPrice = match.product?.price || null;
            
            let diffPercent = null;
            let status = 'NO_COMPETITOR';
            
            if (gPrice !== null) {
                diffPercent = ((gPrice - vPrice) / vPrice) * 100;
                status = diffPercent > 0 ? 'WIN' : 'LOSS';
            }
            
            return {
                id: `visuar-${index}`,
                name: vProduct.name,
                brand: vProduct.brand,
                btu: vProduct.btu,
                is_inverter: vProduct.is_inverter,
                visuar_price: vPrice,
                gg_price: gPrice,
                gg_name: match.product?.name || null,
                gg_brand: match.product?.brand || null,
                lowest_comp: gPrice,
                diff_percent: diffPercent ? parseFloat(diffPercent.toFixed(2)) : null,
                status: status,
                match_level: match.classification.level,
                match_label: match.classification.label,
                match_color: match.classification.color,
                match_warning: match.classification.warning,
                match_percentage: match.matchResult?.percentage || 0,
                visuar_attrs: match.visuarAttr,
                gg_attrs: match.ggAttr,
                last_updated: new Date().toISOString()
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
            no_data: rows.filter(r => r.status === 'NO_COMPETITOR').length
        };
        
        return new Response(JSON.stringify({ rows, stats }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        });
    } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
    }
}
