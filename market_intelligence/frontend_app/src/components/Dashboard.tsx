import React, { useState, useEffect } from 'react';
import { TrendingDown, TrendingUp, DollarSign, Activity, AlertCircle, RefreshCw, Layers, Inbox, CheckCircle, XCircle, Zap, Link, BarChart2, Scale, List } from 'lucide-react';
import { DashboardKPIs } from './DashboardKPIs';
import { PriceHistoryChart } from './PriceHistoryChart';
import { MasterProductList } from './MasterProductList';
import { VisuarCatalog } from './VisuarCatalog';
import { GGCatalog } from './GGCatalog';

export default function Dashboard() {
    const [activeTab, setActiveTab] = useState('MAIN');
    const [rows, setRows] = useState([]);
    const [pendingMappings, setPendingMappings] = useState([]);
    const [unmappedProducts, setUnmappedProducts] = useState([]);
    const [canonicalOptions, setCanonicalOptions] = useState([]);
    const [selectedCanonical, setSelectedCanonical] = useState<Record<number, string>>({});

    // Comparador Ad-Hoc State
    const [allProductsData, setAllProductsData] = useState<{ visuar: any[], competitors: any[] }>({ visuar: [], competitors: [] });
    const [compareVisuarId, setCompareVisuarId] = useState('');
    const [compareCompetitorId, setCompareCompetitorId] = useState('');

    const [loading, setLoading] = useState(true);

    const loadData = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/data.json');
            const data = await response.json();
            setRows(data);

            const pendingRes = await fetch('/api/pending_mappings.json');
            const pendingData = await pendingRes.json();
            setPendingMappings(pendingData);

            const unmappedRes = await fetch('/api/unmapped_products.json');
            setUnmappedProducts(await unmappedRes.json());

            const canRes = await fetch('/api/canonical_products.json');
            setCanonicalOptions(await canRes.json());

            const allProductsRes = await fetch('/api/all_products_with_prices.json');
            setAllProductsData(await allProductsRes.json());
        } catch (e) {
            console.error(e);
        }
        setLoading(false);
    };

    const handleApproval = async (mapping_id: number, action: 'approve' | 'reject') => {
        try {
            const res = await fetch('/api/approve_mapping.json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mapping_id, action })
            });
            if (res.ok) {
                setPendingMappings(prev => prev.filter((p: any) => p.mapping_id !== mapping_id));
                if (action === 'approve') loadData(); // Reload main dashboard
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handleVersusMap = async (competitor_product_id: number) => {
        const canonical_product_id = selectedCanonical[competitor_product_id];
        if (!canonical_product_id) return;

        try {
            const res = await fetch('/api/force_map.json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ competitor_product_id, canonical_product_id })
            });
            if (res.ok) {
                setUnmappedProducts(prev => prev.filter((p: any) => p.id !== competitor_product_id));
                loadData(); // Rehydrate everything
            }
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const totalWins = rows.filter((r: any) => r.status === 'WIN').length;
    const totalLosses = rows.filter((r: any) => r.status === 'LOSS').length;

    // Calcular promedios para KPIs
    const sumLosses = rows.filter((r: any) => r.status === 'LOSS').reduce((acc: number, curr: any) => acc + curr.diff_percent, 0);
    const avgLoss = totalLosses > 0 ? (sumLosses / totalLosses).toFixed(2) : '0.00';

    const sumWins = rows.filter((r: any) => r.status === 'WIN' && r.diff_percent !== null).reduce((acc: number, curr: any) => acc + curr.diff_percent, 0);
    const avgWin = totalWins > 0 ? Math.abs(sumWins / totalWins).toFixed(2) : '0.00';

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 p-8 font-sans selection:bg-indigo-500/30">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Encabezado Ejecutivo */}
                <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-white flex items-center gap-3 tracking-tight">
                            <Layers className="text-indigo-400" size={32} />
                            Market Intelligence Engine
                        </h1>
                        <p className="text-slate-400 mt-1">Comparativa estructurada de precios (Visuar vs Competencia)</p>
                    </div>
                    <button onClick={loadData} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 transition-colors rounded-lg font-medium shadow-lg shadow-indigo-900/20 text-white">
                        <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                        Sincronizar Data Local
                    </button>
                </header>

                {/* Tabs Navigation */}
                <div className="flex gap-4 border-b border-slate-800 pb-2">
                    <button
                        onClick={() => setActiveTab('MAIN')}
                        className={`pb-2 px-2 font-medium flex items-center gap-2 transition-colors ${activeTab === 'MAIN' ? 'text-indigo-400 border-b-2 border-indigo-400' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <Activity size={18} />
                        Panel Principal
                    </button>
                    <button
                        onClick={() => setActiveTab('INBOX')}
                        className={`pb-2 px-2 font-medium flex items-center gap-2 transition-colors ${activeTab === 'INBOX' ? 'text-indigo-400 border-b-2 border-indigo-400' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <Inbox size={18} />
                        Bandeja de Aprobación
                        {pendingMappings.length > 0 && (
                            <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full ml-1 animate-pulse">
                                {pendingMappings.length}
                            </span>
                        )}
                    </button>
                    <button
                        onClick={() => setActiveTab('VERSUS')}
                        className={`pb-2 px-2 font-medium flex items-center gap-2 transition-colors ${activeTab === 'VERSUS' ? 'text-fuchsia-400 border-b-2 border-fuchsia-400' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <Zap size={18} />
                        Modo Versus
                        {unmappedProducts.length > 0 && (
                            <span className="bg-slate-800 text-slate-300 text-xs px-2 py-0.5 rounded-full ml-1">
                                {unmappedProducts.length} huerfanos
                            </span>
                        )}
                    </button>
                    <button
                        onClick={() => setActiveTab('COMPARADOR')}
                        className={`pb-2 px-2 font-medium flex items-center gap-2 transition-colors ${activeTab === 'COMPARADOR' ? 'text-amber-400 border-b-2 border-amber-400' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <Scale size={18} />
                        Comparador Libre
                    </button>
                    <button
                        onClick={() => setActiveTab('CATALOGO')}
                        className={`pb-2 px-2 font-medium flex items-center gap-2 transition-colors ${activeTab === 'CATALOGO' ? 'text-teal-400 border-b-2 border-teal-400' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <List size={18} />
                        Catálogo Visuar
                    </button>
                    <button
                        onClick={() => setActiveTab('CATALOGO_GG')}
                        className={`pb-2 px-2 font-medium flex items-center gap-2 transition-colors ${activeTab === 'CATALOGO_GG' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <List size={18} />
                        Catálogo GG
                    </button>
                </div>

                {activeTab === 'MAIN' && (
                    <>

                        {/* Dashboard KPIs */}
                        <DashboardKPIs />
                        <PriceHistoryChart />

                        {/* Tabla de Datos Premium */}
                        <MasterProductList products={rows.map((row: any) => ({
                            id: row.id,
                            master_name: row.name,
                            visuar_price: row.visuar_price?.toLocaleString('es-PY') || 'N/A',
                            best_competitor: row.bristol_price ? 'Bristol' : (row.gg_price ? 'Gonzalez Gimenez' : 'N/A'),
                            diff_percent: row.diff_percent || 0,
                            competitors: [
                                ...(row.bristol_price ? [{ name: 'Bristol', diff: row.diff_percent || 0, price: row.bristol_price?.toLocaleString('es-PY'), raw_name: "Scraped Data from Web" }] : [])
                            ]
                        }))} />
                    </>
                )}

                {activeTab === 'INBOX' && (
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl p-6">
                        <div className="border-b border-slate-800 pb-4 mb-6">
                            <h2 className="text-xl font-semibold text-white">Inbox de Mapeos (AI Suggested)</h2>
                            <p className="text-slate-400 mt-1 text-sm">El motor difuso procesó productos similares. Confirma el emparejamiento para agregarlos al cálculo de oportunidades de precios central.</p>
                        </div>

                        {pendingMappings.length === 0 ? (
                            <div className="text-center py-12 text-slate-500">
                                <CheckCircle size={48} className="mx-auto text-emerald-500/50 mb-4" />
                                <p className="text-lg">No hay mapeos pendientes. Todo está enlazado correctamente.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 gap-4">
                                {pendingMappings.map((pm: any) => (
                                    <div key={pm.mapping_id} className="bg-slate-950 border border-slate-800 p-4 rounded-xl flex flex-col lg:flex-row justify-between items-center gap-6 shadow-inner">
                                        <div className="flex-1 w-full">
                                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest bg-slate-800 px-2 py-1 rounded inline-block mb-2">PRODUCTO DETECTADO EN: {pm.competitor_name}</span>
                                            <p className="text-lg font-medium text-white">{pm.raw_name}</p>
                                        </div>

                                        <div className="text-slate-600 hidden lg:block">
                                            ➔
                                        </div>

                                        <div className="flex-1 w-full bg-indigo-900/10 border border-indigo-500/20 p-3 rounded-xl relative">
                                            <span className="absolute -top-3 right-4 bg-indigo-600 text-white text-[10px] uppercase font-bold px-2 py-0.5 rounded-full shadow-lg">
                                                Match Score: {pm.match_score}%
                                            </span>
                                            <span className="text-xs font-bold text-indigo-400 uppercase tracking-widest inline-block mb-1">SUGERENCIA DE ENLACE CANÓNICO (Visuar)</span>
                                            <p className="text-indigo-100 font-medium">{pm.suggested_canonical_name}</p>
                                        </div>

                                        <div className="flex gap-3 w-full lg:w-auto mt-4 lg:mt-0">
                                            <button
                                                onClick={() => handleApproval(pm.mapping_id, 'approve')}
                                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600 hover:text-white transition-all rounded-lg font-medium"
                                            >
                                                <CheckCircle size={18} /> Aprobar
                                            </button>
                                            <button
                                                onClick={() => handleApproval(pm.mapping_id, 'reject')}
                                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600/20 text-red-400 border border-red-500/30 hover:bg-red-600 hover:text-white transition-all rounded-lg font-medium"
                                            >
                                                <XCircle size={18} /> Rechazar
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'VERSUS' && (
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl p-6">
                        <div className="border-b border-slate-800 pb-4 mb-6">
                            <h2 className="text-xl font-semibold text-white flex items-center gap-2"><Zap className="text-fuchsia-500" /> Modo Versus (Enlace Manual)</h2>
                            <p className="text-slate-400 mt-1 text-sm">Productos recolectados que la Inteligencia de Mapeo no pudo enlazar (0% coincidencia). Selecciona la equivalencia local para forzar el vínculo de precios.</p>
                        </div>

                        {unmappedProducts.length === 0 ? (
                            <div className="text-center py-12 text-slate-500">
                                <CheckCircle size={48} className="mx-auto text-slate-700 mb-4" />
                                <p className="text-lg">No hay productos huérfanos en la base de datos.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 gap-4">
                                {unmappedProducts.map((up: any) => (
                                    <div key={up.id} className="bg-slate-950 border border-slate-800 p-4 rounded-xl flex flex-col lg:flex-row justify-between items-center gap-6 shadow-inner transition-all hover:border-slate-700">
                                        <div className="flex-1 w-full">
                                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest bg-slate-800 px-2 py-1 rounded inline-block mb-2">RAW: {up.competitor_name}</span>
                                            <p className="text-lg font-medium text-white">{up.name}</p>
                                        </div>

                                        <div className="text-slate-600 hidden lg:block">
                                            ➔
                                        </div>

                                        <div className="flex-1 w-full relative">
                                            <label className="text-xs font-bold text-fuchsia-400 uppercase tracking-widest mb-2 block">Seleccionar Equivalente Visuar</label>
                                            <select
                                                className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded-lg p-2.5 focus:border-fuchsia-500 focus:ring-1 focus:ring-fuchsia-500 outline-none transition-all"
                                                value={selectedCanonical[up.id] || ""}
                                                onChange={(e) => setSelectedCanonical({ ...selectedCanonical, [up.id]: e.target.value })}
                                            >
                                                <option value="" disabled>-- Selecciona un producto del catálogo --</option>
                                                {canonicalOptions.map((co: any) => (
                                                    <option key={co.id} value={co.id}>
                                                        {co.capacity_btu ? `[${co.capacity_btu / 1000}K BTU ${co.is_inverter ? 'INV' : 'ON/OFF'}] ` : ''}
                                                        {co.name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>

                                        <div className="flex w-full lg:w-auto mt-4 lg:mt-0 items-end">
                                            <button
                                                disabled={!selectedCanonical[up.id]}
                                                onClick={() => handleVersusMap(up.id)}
                                                className="w-full lg:w-auto flex items-center justify-center gap-2 px-6 py-2.5 bg-fuchsia-600 text-white hover:bg-fuchsia-500 transition-all rounded-lg font-medium shadow-lg shadow-fuchsia-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                <Link size={18} /> Forzar Enlace
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'COMPARADOR' && (
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl p-6">
                        <div className="border-b border-slate-800 pb-4 mb-6">
                            <h2 className="text-xl font-semibold text-white flex items-center gap-2"><Scale className="text-amber-500" /> Comparador Ad-Hoc Libre</h2>
                            <p className="text-slate-400 mt-1 text-sm">Selecciona cualquier producto de Visuar y compáralo en vivo con cualquier producto de la competencia extraído por el Web Scraper.</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                            <div className="bg-slate-950 p-6 rounded-xl border border-indigo-900/50 relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 rounded-bl-full -mr-8 -mt-8 pointer-events-none"></div>
                                <h3 className="text-indigo-400 font-bold mb-4 uppercase tracking-wider text-sm">Paso 1: Selecciona Producto Base (Visuar)</h3>
                                <select
                                    className="w-full bg-slate-900 border border-slate-700 text-indigo-100 rounded-lg p-3 outline-none focus:border-indigo-500 hover:border-slate-600 transition-all font-medium py-4 cursor-pointer"
                                    value={compareVisuarId}
                                    onChange={e => setCompareVisuarId(e.target.value)}
                                >
                                    <option value="">-- Elige un Split Visuar --</option>
                                    {allProductsData.visuar.map((p: any) => (
                                        <option key={p.id} value={p.id}>{p.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="bg-slate-950 p-6 rounded-xl border border-rose-900/50 relative overflow-hidden">
                                <div className="absolute top-0 left-0 w-32 h-32 bg-rose-500/5 rounded-br-full -ml-8 -mt-8 pointer-events-none"></div>
                                <h3 className="text-rose-400 font-bold mb-4 uppercase tracking-wider text-sm">Paso 2: Contra quién comparar</h3>
                                <select
                                    className="w-full bg-slate-900 border border-slate-700 text-rose-100 rounded-lg p-3 outline-none focus:border-rose-500 hover:border-slate-600 transition-all font-medium py-4 cursor-pointer"
                                    value={compareCompetitorId}
                                    onChange={e => setCompareCompetitorId(e.target.value)}
                                >
                                    <option value="">-- Elige un competidor --</option>
                                    {allProductsData.competitors.map((p: any) => (
                                        <option key={p.id} value={p.id}>[{p.comp_name}] {p.name}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {compareVisuarId && compareCompetitorId && (() => {
                            const pV = allProductsData.visuar.find((p: any) => p.id.toString() === compareVisuarId);
                            const pC = allProductsData.competitors.find((p: any) => p.id.toString() === compareCompetitorId);
                            if (!pV || !pC) return null;

                            const vPrice = parseFloat(pV.latest_price);
                            const cPrice = parseFloat(pC.latest_price);
                            const diffValue = cPrice - vPrice;
                            const isWin = diffValue > 0;
                            const diffPercent = Math.abs((diffValue / vPrice) * 100).toFixed(2);
                            const maxPrice = Math.max(vPrice, cPrice);

                            const vBar = Math.max(20, (vPrice / maxPrice) * 100);
                            const cBar = Math.max(20, (cPrice / maxPrice) * 100);

                            const formatter = new Intl.NumberFormat('es-PY', { style: 'currency', currency: 'PYG', minimumFractionDigits: 0 });

                            return (
                                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 border border-slate-800 bg-slate-950 p-8 rounded-2xl shadow-2xl relative overflow-hidden">
                                    <div className="text-center mb-8">
                                        <span className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold border shadow-inner ${isWin
                                            ? 'bg-emerald-900/30 text-emerald-400 border-emerald-500/50 shadow-emerald-900/50'
                                            : 'bg-rose-900/30 text-rose-400 border-rose-500/50 shadow-rose-900/50'
                                            }`}>
                                            {isWin ? <TrendingDown size={18} className="text-emerald-500" /> : <TrendingUp size={18} className="text-rose-500" />}
                                            {isWin ? 'VISUAR ES MÁS BARATO (WIN)' : 'VISUAR ES MÁS CARO (LOSS)'}
                                        </span>
                                    </div>

                                    <div className="flex flex-col md:flex-row items-center justify-between gap-12 relative z-10">
                                        <div className="flex-1 w-full text-center">
                                            <div className="text-xs font-bold text-slate-500 bg-slate-900 px-3 py-1 rounded inline-block mb-3 uppercase tracking-widest border border-slate-800">Tu Stock (Visuar)</div>
                                            <h4 className="text-xl font-medium text-white mb-2 leading-snug">{pV.name}</h4>
                                            <div className="text-3xl font-extrabold text-indigo-400">{formatter.format(vPrice)}</div>

                                            <div className="mt-6 bg-slate-900 h-6 w-full rounded-full overflow-hidden flex justify-end shadow-inner border border-slate-800">
                                                <div
                                                    className="h-full bg-indigo-500 rounded-l-full transition-all duration-1000 ease-out"
                                                    style={{ width: `${vBar}%` }}
                                                ></div>
                                            </div>
                                        </div>

                                        <div className="shrink-0 flex flex-col items-center justify-center p-6 bg-slate-900 rounded-full border-4 border-slate-950 -my-6 shadow-2xl relative z-20">
                                            <span className="text-4xl font-black text-white px-2 tracking-tighter block mb-1">VS</span>
                                            <span className={`text-sm font-bold px-2 py-0.5 rounded ${isWin ? 'text-emerald-400 bg-emerald-900/30' : 'text-rose-400 bg-rose-900/30'}`}>
                                                {isWin ? '-' : '+'}{formatter.format(Math.abs(diffValue))} ({diffPercent}%)
                                            </span>
                                        </div>

                                        <div className="flex-1 w-full text-center">
                                            <div className="text-xs font-bold text-slate-500 bg-slate-900 px-3 py-1 rounded inline-block mb-3 uppercase tracking-widest border border-slate-800">Competencia ({pC.comp_name})</div>
                                            <h4 className="text-xl font-medium text-white mb-2 leading-snug break-words">{pC.name}</h4>
                                            <div className="text-3xl font-extrabold text-rose-400">{formatter.format(cPrice)}</div>

                                            <div className="mt-6 bg-slate-900 h-6 w-full rounded-full overflow-hidden flex justify-start shadow-inner border border-slate-800">
                                                <div
                                                    className="h-full bg-rose-500 rounded-r-full transition-all duration-1000 ease-out"
                                                    style={{ width: `${cBar}%` }}
                                                ></div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Decoration */}
                                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/10 via-slate-950/0 to-slate-950/0 pointer-events-none rounded-xl"></div>
                                </div>
                            );
                        })()}
                    </div>
                )}

                {activeTab === 'CATALOGO' && (
                    <VisuarCatalog />
                )}

                {activeTab === 'CATALOGO_GG' && (
                    <GGCatalog />
                )}
            </div>
        </div>
    );
}
