import React, { useEffect, useState } from 'react';
import { TrendingDown, TrendingUp, Minus, BarChart3 } from 'lucide-react';

interface ComparisonRow {
    name: string;
    brand: string;
    btu: number | null;
    visuarPrice: number;
    ggPrice: number | null;
    ggName: string | null;
    diffPercent: number | null;
    status: 'WIN' | 'LOSS' | 'EQUAL' | 'NO_DATA';
}

export const PriceHistoryChart = ({ data = [] }: { data?: any[] }) => {
    const [comparisons, setComparisons] = useState<ComparisonRow[]>([]);
    const [filter, setFilter] = useState<'ALL' | 'WIN' | 'LOSS'>('ALL');

    useEffect(() => {
        // Only include rows that have both prices (gg_price exists)
        const matched: ComparisonRow[] = data
            .filter((r: any) => r.gg_price != null)
            .map((r: any) => ({
                name: r.name,
                brand: r.brand,
                btu: r.btu,
                visuarPrice: r.visuar_price,
                ggPrice: r.gg_price,
                ggName: r.gg_name,
                diffPercent: r.diff_percent,
                status: r.status === 'WIN' ? 'WIN' : r.status === 'LOSS' ? 'LOSS' : 'EQUAL'
            }))
            .sort((a: ComparisonRow, b: ComparisonRow) => {
                const aDiff = Math.abs(a.diffPercent || 0);
                const bDiff = Math.abs(b.diffPercent || 0);
                return bDiff - aDiff;
            });

        setComparisons(matched);
    }, [data]);

    const formatter = new Intl.NumberFormat('es-PY', { style: 'currency', currency: 'PYG', minimumFractionDigits: 0 });

    const filtered = filter === 'ALL'
        ? comparisons
        : comparisons.filter(c => c.status === filter);

    const wins = comparisons.filter(c => c.status === 'WIN').length;
    const losses = comparisons.filter(c => c.status === 'LOSS').length;
    const totalMatched = comparisons.length;

    if (data.length === 0) {
        return (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl mt-6 p-6">
                <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                    <BarChart3 className="text-indigo-400" size={22} />
                    Comparacion Actual: Visuar vs GG
                </h3>
                <div className="flex items-center justify-center h-32">
                    <p className="text-slate-400">Cargando datos de comparacion...</p>
                </div>
            </div>
        );
    }

    if (comparisons.length === 0) {
        return (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl mt-6 p-6">
                <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                    <BarChart3 className="text-indigo-400" size={22} />
                    Comparacion Actual: Visuar vs GG
                </h3>
                <div className="flex items-center justify-center h-32 bg-slate-950/50 rounded-xl mt-6 border border-slate-800/80">
                    <p className="text-slate-400 italic">No hay productos exactos comparables en González Giménez en este momento.</p>
                </div>
            </div>
        );
    }

    // Calculate max price for bar scaling
    const maxPrice = Math.max(
        ...comparisons.map(c => Math.max(c.visuarPrice, c.ggPrice || 0))
    );

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl mt-6 p-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
                <div>
                    <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                        <BarChart3 className="text-indigo-400" size={22} />
                        Comparacion Actual: Visuar vs GG
                    </h3>
                    <p className="text-slate-500 text-sm mt-1">
                        {totalMatched} productos comparables encontrados
                    </p>
                </div>

                {/* Filter buttons */}
                <div className="flex gap-2">
                    <button
                        onClick={() => setFilter('ALL')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${filter === 'ALL'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                            }`}
                    >
                        Todos ({totalMatched})
                    </button>
                    <button
                        onClick={() => setFilter('WIN')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${filter === 'WIN'
                            ? 'bg-emerald-600 text-white'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                            }`}
                    >
                        Ganamos ({wins})
                    </button>
                    <button
                        onClick={() => setFilter('LOSS')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${filter === 'LOSS'
                            ? 'bg-rose-600 text-white'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                            }`}
                    >
                        Perdemos ({losses})
                    </button>
                </div>
            </div>

            {/* Visual Comparison Bars */}
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                {filtered.map((item, idx) => {
                    const vBarWidth = (item.visuarPrice / maxPrice) * 100;
                    const gBarWidth = ((item.ggPrice || 0) / maxPrice) * 100;
                    const isWin = item.status === 'WIN';
                    const isLoss = item.status === 'LOSS';

                    return (
                        <div
                            key={idx}
                            className="bg-slate-950 rounded-xl p-4 border border-slate-800 hover:border-slate-700 transition-all group"
                        >
                            {/* Product header */}
                            <div className="flex justify-between items-start mb-3">
                                <div className="flex-1 min-w-0">
                                    <h4 className="text-sm font-medium text-white truncate" title={item.name}>
                                        {item.name}
                                    </h4>
                                    <span className="text-xs text-slate-500">
                                        {item.brand} {item.btu ? `| ${(item.btu / 1000).toFixed(0)}K BTU` : ''}
                                    </span>
                                </div>
                                <span className={`shrink-0 ml-3 inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border ${isWin
                                    ? 'bg-emerald-900/30 text-emerald-400 border-emerald-500/40'
                                    : isLoss
                                        ? 'bg-rose-900/30 text-rose-400 border-rose-500/40'
                                        : 'bg-slate-800 text-slate-400 border-slate-700'
                                    }`}>
                                    {isWin ? <TrendingDown size={12} /> : isLoss ? <TrendingUp size={12} /> : <Minus size={12} />}
                                    {item.diffPercent !== null ? `${Math.abs(item.diffPercent).toFixed(1)}%` : '-'}
                                </span>
                            </div>

                            {/* Bars */}
                            <div className="space-y-1.5">
                                {/* Visuar bar */}
                                <div className="flex items-center gap-3">
                                    <span className="text-[10px] font-bold text-indigo-400 w-12 shrink-0 text-right uppercase tracking-wider">Visuar</span>
                                    <div className="flex-1 bg-slate-900 h-6 rounded-md overflow-hidden relative">
                                        <div
                                            className="h-full bg-gradient-to-r from-indigo-600 to-indigo-500 rounded-md transition-all duration-700 flex items-center justify-end pr-2"
                                            style={{ width: `${Math.max(vBarWidth, 5)}%` }}
                                        >
                                            <span className="text-[10px] font-bold text-white whitespace-nowrap">
                                                {formatter.format(item.visuarPrice)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                {/* GG bar */}
                                <div className="flex items-center gap-3">
                                    <span className="text-[10px] font-bold text-blue-400 w-12 shrink-0 text-right uppercase tracking-wider">GG</span>
                                    <div className="flex-1 bg-slate-900 h-6 rounded-md overflow-hidden relative">
                                        <div
                                            className={`h-full rounded-md transition-all duration-700 flex items-center justify-end pr-2 ${isWin
                                                ? 'bg-gradient-to-r from-blue-600 to-blue-500'
                                                : 'bg-gradient-to-r from-rose-600 to-rose-500'
                                                }`}
                                            style={{ width: `${Math.max(gBarWidth, 5)}%` }}
                                        >
                                            <span className="text-[10px] font-bold text-white whitespace-nowrap">
                                                {item.ggPrice ? formatter.format(item.ggPrice) : 'N/A'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* GG product name on hover */}
                            {item.ggName && (
                                <div className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <span className="text-[10px] text-slate-500 italic">GG: {item.ggName}</span>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
