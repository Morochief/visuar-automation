import React, { useState, useEffect } from 'react';
import { TrendingDown, TrendingUp, DollarSign, Activity, AlertCircle, RefreshCw, Layers } from 'lucide-react';

export default function Dashboard() {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadData = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/data.json');
            const data = await response.json();
            setRows(data);
        } catch (e) {
            console.error(e);
        }
        setLoading(false);
    };

    useEffect(() => {
        loadData();
    }, []);

    const totalWins = rows.filter(r => r.status === 'WIN').length;
    const totalLosses = rows.filter(r => r.status === 'LOSS').length;

    // Calcular promedios para KPIs
    const sumLosses = rows.filter(r => r.status === 'LOSS').reduce((acc, curr) => acc + curr.diff_percent, 0);
    const avgLoss = totalLosses > 0 ? (sumLosses / totalLosses).toFixed(2) : '0.00';

    const sumWins = rows.filter(r => r.status === 'WIN' && curr.diff_percent !== null).reduce((acc, curr) => acc + curr.diff_percent, 0);
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
                        <p className="text-slate-400 mt-1">Comparativa estructurada de precios (Visuar vs Bristol)</p>
                    </div>
                    <button onClick={loadData} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 transition-colors rounded-lg font-medium shadow-lg shadow-indigo-900/20 text-white">
                        <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                        Sincronizar Data Local
                    </button>
                </header>

                {/* Dashboard KPIs */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
                        <div className="flex justify-between items-start">
                            <div>
                                <p className="text-slate-400 font-medium">Oportunidades de Rebaja</p>
                                <h3 className="text-4xl font-bold text-white mt-2">{totalLosses}</h3>
                            </div>
                            <div className="p-3 bg-red-500/10 text-red-400 rounded-xl">
                                <AlertCircle size={24} />
                            </div>
                        </div>
                        <p className="text-sm mt-4 text-slate-500 flex items-center gap-2">
                            <span className="text-red-400 flex items-center"><TrendingUp size={14} className="mr-1" /> {avgLoss}%</span>
                            margen negativo prom.
                        </p>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
                        <div className="flex justify-between items-start">
                            <div>
                                <p className="text-slate-400 font-medium">Ventaja Competitiva</p>
                                <h3 className="text-4xl font-bold text-white mt-2">{totalWins}</h3>
                            </div>
                            <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl">
                                <TrendingDown size={24} />
                            </div>
                        </div>
                        <p className="text-sm mt-4 text-slate-500 flex items-center gap-2">
                            <span className="text-emerald-400 flex items-center"><TrendingDown size={14} className="mr-1" /> {avgWin}%</span>
                            más baratos que Bristol
                        </p>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
                        <div className="flex justify-between items-start">
                            <div>
                                <p className="text-slate-400 font-medium">Última Sincronización</p>
                                <h3 className="text-2xl font-bold text-white mt-4">{rows.length > 0 ? "Local (SQLite)" : "Sin Conexión"}</h3>
                            </div>
                            <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl">
                                <Activity size={24} />
                            </div>
                        </div>
                        <p className="text-sm mt-4 text-slate-500">
                            Scraping cruzado cargado con Integridad
                        </p>
                    </div>
                </div>

                {/* Tabla de Datos Premium */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
                    <div className="p-6 border-b border-slate-800 flex justify-between items-center">
                        <h2 className="text-xl font-semibold text-white">Análisis Retrospectivo</h2>
                        <span className="text-sm text-slate-500 uppercase tracking-widest font-semibold">{rows.length} PRODUCTOS MAPEDADOS</span>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-slate-950/50 text-slate-400 text-sm uppercase tracking-wider">
                                    <th className="px-6 py-4 font-medium">Producto (Canonical ID)</th>
                                    <th className="px-6 py-4 font-medium">Visuar (Nativo)</th>
                                    <th className="px-6 py-4 font-medium">Bristol (Competencia)</th>
                                    <th className="px-6 py-4 font-medium">Margen Relativo</th>
                                    <th className="px-6 py-4 font-medium text-right">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {loading && (
                                    <tr><td colSpan="5" className="p-6 text-center text-slate-500">Sincronizando la Base de Datos...</td></tr>
                                )}
                                {!loading && rows.map((row) => (
                                    <tr key={row.id} className="hover:bg-slate-800/50 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded bg-slate-800 flex items-center justify-center">
                                                    <DollarSign className="text-slate-500" size={18} />
                                                </div>
                                                <div>
                                                    <p className="font-semibold text-slate-200">{row.name}</p>
                                                    <p className="text-xs text-slate-500 font-mono mt-1">{row.id.substring(0, 8)}...</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-slate-300 font-medium">
                                            Gs. {row.visuar_price?.toLocaleString('es-PY') || 'N/A'}
                                        </td>
                                        <td className="px-6 py-4 text-slate-300">
                                            Gs. {row.bristol_price?.toLocaleString('es-PY') || 'N/A'}
                                        </td>
                                        <td className="px-6 py-4">
                                            {row.diff_percent < 0 ? (
                                                <span className="text-emerald-400 font-medium flex items-center gap-1">
                                                    {row.diff_percent}%
                                                </span>
                                            ) : row.diff_percent > 0 ? (
                                                <span className="text-red-400 font-medium flex items-center gap-1">
                                                    +{row.diff_percent}%
                                                </span>
                                            ) : (
                                                <span className="text-slate-400 font-medium">0.00%</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            {row.status === 'WIN' && (
                                                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                                    COMPETITIVO
                                                </span>
                                            )}
                                            {row.status === 'LOSS' && (
                                                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
                                                    SOBREPRECIO
                                                </span>
                                            )}
                                            {row.status === 'EQUAL' && (
                                                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
                                                    EMPATADO
                                                </span>
                                            )}
                                            {row.status === 'COMPETITOR_OUT_OF_STOCK' && (
                                                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-yellow-500/10 text-yellow-500 border border-yellow-500/20">
                                                    BRISTOL S/ STOCK
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>
        </div>
    );
}
