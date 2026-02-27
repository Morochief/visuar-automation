import React, { useState, useEffect } from 'react';
import { TrendingDown, TrendingUp, Activity, RefreshCw, Layers, Scale, List } from 'lucide-react';
import { DashboardKPIs } from './DashboardKPIs';
import { PriceHistoryChart } from './PriceHistoryChart';
import { MasterProductList } from './MasterProductList';
import { VisuarCatalog } from './VisuarCatalog';
import { GGCatalog } from './GGCatalog';

export default function Dashboard() {
    const [activeTab, setActiveTab] = useState('MAIN');
    const [rows, setRows] = useState([]);
    const [scrapedData, setScrapedData] = useState<{ visuar: any[], gg: any[] }>({ visuar: [], gg: [] });
    
    // Comparador Libre - State
    const [compareVisuarId, setCompareVisuarId] = useState('');
    const [compareGgId, setCompareGgId] = useState('');

    const [loading, setLoading] = useState(true);

    const loadData = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/data.json');
            const data = await response.json();
            // La API ahora devuelve { rows, stats }
            setRows(data.rows || data);

            const scrapedRes = await fetch('/api/scraped_data.json');
            const scrapedData = await scrapedRes.json();
            setScrapedData(scrapedData);
        } catch (e) {
            console.error(e);
        }
        setLoading(false);
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
                        <p className="text-slate-400 mt-1">Comparativa de precios Visuar vs Gonzalez Gimenez</p>
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
                            gg_price: row.gg_price,
                            best_competitor: row.gg_brand || 'Sin competencia',
                            diff_percent: row.diff_percent || 0,
                            match_level: row.match_level || 'NINGUNO',
                            match_label: row.match_label || 'Sin Match',
                            match_color: row.match_color || 'red',
                            match_percentage: row.match_percentage || 0,
                            competitors: []
                        }))} />
                    </>
                )}

                {activeTab === 'COMPARADOR' && (
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl p-6">
                        <div className="border-b border-slate-800 pb-4 mb-6">
                            <h2 className="text-xl font-semibold text-white flex items-center gap-2"><Scale className="text-amber-500" /> Comparador Libre</h2>
                            <p className="text-slate-400 mt-1 text-sm">Selecciona un producto de Visuar y compáralo con un producto de GG.</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                            <div className="bg-slate-950 p-6 rounded-xl border border-indigo-900/50">
                                <h3 className="text-indigo-400 font-bold mb-4 uppercase tracking-wider text-sm">Producto Visuar</h3>
                                <select
                                    className="w-full bg-slate-900 border border-slate-700 text-indigo-100 rounded-lg p-3 outline-none focus:border-indigo-500 hover:border-slate-600 transition-all font-medium cursor-pointer"
                                    value={compareVisuarId}
                                    onChange={e => setCompareVisuarId(e.target.value)}
                                >
                                    <option value="">-- Selecciona un producto --</option>
                                    {scrapedData.visuar.map((p: any, idx: number) => (
                                        <option key={idx} value={idx}>{p.brand} - {p.name.substring(0, 50)}... (Gs. {p.price?.toLocaleString('es-PY')})</option>
                                    ))}
                                </select>
                            </div>

                            <div className="bg-slate-950 p-6 rounded-xl border border-blue-900/50">
                                <h3 className="text-blue-400 font-bold mb-4 uppercase tracking-wider text-sm">Producto GG</h3>
                                <select
                                    className="w-full bg-slate-900 border border-slate-700 text-blue-100 rounded-lg p-3 outline-none focus:border-blue-500 hover:border-slate-600 transition-all font-medium cursor-pointer"
                                    value={compareGgId}
                                    onChange={e => setCompareGgId(e.target.value)}
                                >
                                    <option value="">-- Selecciona un producto --</option>
                                    {scrapedData.gg.map((p: any, idx: number) => (
                                        <option key={idx} value={idx}>{p.brand} - {p.name.substring(0, 50)}... (Gs. {p.price?.toLocaleString('es-PY')})</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {compareVisuarId !== '' && compareGgId !== '' && (() => {
                            const pV = scrapedData.visuar[parseInt(compareVisuarId)];
                            const pG = scrapedData.gg[parseInt(compareGgId)];
                            if (!pV || !pG) return null;

                            const vPrice = pV.price;
                            const gPrice = pG.price;
                            const diffValue = gPrice - vPrice;
                            const isWin = diffValue > 0;
                            const diffPercent = Math.abs((diffValue / vPrice) * 100).toFixed(1);
                            const maxPrice = Math.max(vPrice, gPrice);
                            const vBar = Math.max(20, (vPrice / maxPrice) * 100);
                            const gBar = Math.max(20, (gPrice / maxPrice) * 100);
                            const formatter = new Intl.NumberFormat('es-PY', { style: 'currency', currency: 'PYG', minimumFractionDigits: 0 });

                            return (
                                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 border border-slate-800 bg-slate-950 p-8 rounded-2xl shadow-2xl">
                                    <div className="text-center mb-8">
                                        <span className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold border ${isWin
                                            ? 'bg-emerald-900/30 text-emerald-400 border-emerald-500/50'
                                            : 'bg-rose-900/30 text-rose-400 border-rose-500/50'
                                            }`}>
                                            {isWin ? <TrendingDown size={18} className="text-emerald-500" /> : <TrendingUp size={18} className="text-rose-500" />}
                                            {isWin ? 'VISUAR ES MÁS BARATO (WIN)' : 'GG ES MÁS BARATO (LOSS)'}
                                        </span>
                                    </div>

                                    <div className="flex flex-col md:flex-row items-center justify-between gap-12">
                                        <div className="flex-1 w-full text-center">
                                            <div className="text-xs font-bold text-slate-500 bg-slate-900 px-3 py-1 rounded inline-block mb-3 uppercase tracking-widest border border-slate-800">Visuar</div>
                                            <h4 className="text-sm font-medium text-white mb-2 leading-snug">{pV.name}</h4>
                                            <div className="text-2xl font-extrabold text-indigo-400">{formatter.format(vPrice)}</div>
                                            <div className="mt-4 bg-slate-900 h-4 w-full rounded-full overflow-hidden flex justify-end shadow-inner border border-slate-800">
                                                <div className="h-full bg-indigo-500 rounded-l-full" style={{ width: `${vBar}%` }}></div>
                                            </div>
                                        </div>

                                        <div className="shrink-0 flex flex-col items-center justify-center p-4 bg-slate-900 rounded-full border-4 border-slate-950">
                                            <span className="text-2xl font-black text-white px-2">VS</span>
                                            <span className={`text-xs font-bold px-2 py-0.5 rounded ${isWin ? 'text-emerald-400 bg-emerald-900/30' : 'text-rose-400 bg-rose-900/30'}`}>
                                                {isWin ? '-' : '+'}{formatter.format(Math.abs(diffValue))} ({diffPercent}%)
                                            </span>
                                        </div>

                                        <div className="flex-1 w-full text-center">
                                            <div className="text-xs font-bold text-slate-500 bg-slate-900 px-3 py-1 rounded inline-block mb-3 uppercase tracking-widest border border-slate-800">GG</div>
                                            <h4 className="text-sm font-medium text-white mb-2 leading-snug break-words">{pG.name}</h4>
                                            <div className="text-2xl font-extrabold text-blue-400">{formatter.format(gPrice)}</div>
                                            <div className="mt-4 bg-slate-900 h-4 w-full rounded-full overflow-hidden flex justify-start shadow-inner border border-slate-800">
                                                <div className="h-full bg-blue-500 rounded-r-full" style={{ width: `${gBar}%` }}></div>
                                            </div>
                                        </div>
                                    </div>
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
