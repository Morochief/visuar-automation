import React, { useEffect, useState } from 'react';
import { TrendingDown, TrendingUp, CheckCircle, AlertTriangle, XCircle, Target, Layers } from 'lucide-react';

export const DashboardKPIs = () => {
    const [data, setData] = useState<any>(null);
    const [stats, setStats] = useState({
        wins: 0,
        losses: 0,
        total: 0,
        avgDiff: 0,
        exact_match: 0,
        partial_match: 0,
        no_match: 0
    });
    
    useEffect(() => {
        fetch('/api/data.json')
            .then(res => res.json())
            .then(apiData => {
                // La API ahora devuelve { rows, stats }
                const rows = apiData.rows || apiData;
                const apiStats = apiData.stats;
                
                const wins = rows.filter((d: any) => d.status === 'WIN').length;
                const losses = rows.filter((d: any) => d.status === 'LOSS').length;
                const total = rows.length;
                const lossItems = rows.filter((d: any) => d.status === 'LOSS' && d.diff_percent);
                const avgDiff = lossItems.length > 0 
                    ? lossItems.reduce((acc: number, d: any) => acc + Math.abs(d.diff_percent), 0) / lossItems.length 
                    : 0;
                
                const exact_match = rows.filter((d: any) => d.match_level === 'EXACTO').length;
                const partial_match = rows.filter((d: any) => d.match_level === 'PARCIAL').length;
                const no_match = rows.filter((d: any) => d.match_level === 'NINGUNO' || d.match_level === 'NINGUN').length;
                
                setStats({ wins, losses, total, avgDiff, exact_match, partial_match, no_match });
                setData(apiData);
            });
    }, []);
    
    const formatter = new Intl.NumberFormat('es-PY', { style: 'currency', currency: 'PYG', minimumFractionDigits: 0 });
    
    return (
        <div className="space-y-6 mb-8">
            {/* Stats de Matching */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center gap-3">
                    <div className="p-2 bg-emerald-500/20 rounded-lg">
                        <CheckCircle className="text-emerald-400" size={20} />
                    </div>
                    <div>
                        <p className="text-slate-400 text-xs uppercase tracking-wider">Match Exacto</p>
                        <p className="text-xl font-bold text-white">{stats.exact_match}</p>
                    </div>
                </div>
                
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center gap-3">
                    <div className="p-2 bg-amber-500/20 rounded-lg">
                        <AlertTriangle className="text-amber-400" size={20} />
                    </div>
                    <div>
                        <p className="text-slate-400 text-xs uppercase tracking-wider">Match Parcial</p>
                        <p className="text-xl font-bold text-white">{stats.partial_match}</p>
                    </div>
                </div>
                
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center gap-3">
                    <div className="p-2 bg-rose-500/20 rounded-lg">
                        <XCircle className="text-rose-400" size={20} />
                    </div>
                    <div>
                        <p className="text-slate-400 text-xs uppercase tracking-wider">Sin Competidor</p>
                        <p className="text-xl font-bold text-white">{stats.no_match}</p>
                    </div>
                </div>
                
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center gap-3">
                    <div className="p-2 bg-indigo-500/20 rounded-lg">
                        <Layers className="text-indigo-400" size={20} />
                    </div>
                    <div>
                        <p className="text-slate-400 text-xs uppercase tracking-wider">Total Productos</p>
                        <p className="text-xl font-bold text-white">{stats.total}</p>
                    </div>
                </div>
            </div>
            
            {/* Stats de Precios */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-slate-900 border-t-4 border-rose-500 border-x border-b border-slate-800 p-6 rounded-2xl rounded-t-none shadow-xl">
                    <p className="text-slate-400 font-medium">Productos donde GG es más barato</p>
                    <h3 className="text-3xl font-bold text-white mt-2">{stats.losses} SKUs</h3>
                    <div className="mt-4 flex items-center text-rose-400 bg-rose-500/10 w-fit px-2 py-1 rounded text-xs font-semibold">
                        <TrendingDown size={14} className="mr-1" />
                        Diferencia promedio: {stats.avgDiff.toFixed(1)}%
                    </div>
                </div>

                <div className="bg-slate-900 border-t-4 border-emerald-500 border-x border-b border-slate-800 p-6 rounded-2xl rounded-t-none shadow-xl">
                    <p className="text-slate-400 font-medium">Productos donde Visuar es más barato</p>
                    <h3 className="text-3xl font-bold text-white mt-2">{stats.wins} SKUs</h3>
                    <div className="mt-4 flex items-center text-emerald-400 bg-emerald-500/10 w-fit px-2 py-1 rounded text-xs font-semibold">
                        <TrendingUp size={14} className="mr-1" />
                        Ventaja competitiva
                    </div>
                </div>
                
                <div className="bg-slate-900 border-t-4 border-indigo-500 border-x border-b border-slate-800 p-6 rounded-2xl rounded-t-none shadow-xl">
                    <p className="text-slate-400 font-medium">Comparabilidad</p>
                    <h3 className="text-3xl font-bold text-white mt-2">
                        {Math.round(((stats.exact_match + stats.partial_match) / stats.total) * 100)}%
                    </h3>
                    <div className="mt-4 flex items-center text-indigo-400 bg-indigo-500/10 w-fit px-2 py-1 rounded text-xs font-semibold">
                        <Target size={14} className="mr-1" />
                        {stats.exact_match + stats.partial_match} de {stats.total} productos
                    </div>
                </div>
            </div>
        </div>
    );
};
