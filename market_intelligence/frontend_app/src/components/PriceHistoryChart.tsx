import React from 'react';

const chartdata = [
    { date: "1 Feb", "Visuar": 2970000, "Bristol": 2800000, "Tupi": 2850000, "V": 100, "B": 60, "T": 80 },
    { date: "10 Feb", "Visuar": 2970000, "Bristol": 2600000, "Tupi": 2850000, "V": 100, "B": 20, "T": 80 },
    { date: "20 Feb", "Visuar": 2970000, "Bristol": 2579000, "Tupi": 2700000, "V": 100, "B": 10, "T": 50 },
];

export const PriceHistoryChart = () => (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl mt-6 p-6">
        <h3 className="text-xl font-semibold text-white mb-6">Guerra de Precios: Split Samsung 12.000 BTU Inverter</h3>

        <div className="h-72 w-full flex items-end justify-between gap-4 mt-4 relative">
            <div className="absolute top-0 right-0 flex gap-4">
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-indigo-500"></span><span className="text-xs text-slate-400">Visuar</span></div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-rose-500"></span><span className="text-xs text-slate-400">Bristol</span></div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-amber-500"></span><span className="text-xs text-slate-400">Tupi</span></div>
            </div>

            {chartdata.map((point, i) => (
                <div key={i} className="flex-1 flex flex-col items-center justify-end h-full gap-2 relative group">
                    <div className="absolute -top-12 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800 border border-slate-700 text-white text-xs p-2 rounded shadow-lg pointer-events-none z-10 w-full text-center">
                        <div className="text-indigo-400 shrink-0 tabular-nums">V: {point.Visuar.toLocaleString('es-PY')}</div>
                        <div className="text-rose-400 shrink-0 tabular-nums">B: {point.Bristol.toLocaleString('es-PY')}</div>
                        <div className="text-amber-400 shrink-0 tabular-nums">T: {point.Tupi.toLocaleString('es-PY')}</div>
                    </div>

                    <div className="w-full flex justify-center items-end gap-1 h-full pt-8">
                        <div className="w-1/3 min-w-[4px] bg-indigo-500/80 hover:bg-indigo-400 rounded-t-sm transition-all" style={{ height: `${point.V}%` }}></div>
                        <div className="w-1/3 min-w-[4px] bg-rose-500/80 hover:bg-rose-400 rounded-t-sm transition-all" style={{ height: `${point.B}%` }}></div>
                        <div className="w-1/3 min-w-[4px] bg-amber-500/80 hover:bg-amber-400 rounded-t-sm transition-all" style={{ height: `${point.T}%` }}></div>
                    </div>
                    <span className="text-xs text-slate-500 font-medium mt-2">{point.date}</span>
                </div>
            ))}

            <div className="absolute bottom-6 w-full h-px bg-slate-800/50 -z-10"></div>
            <div className="absolute bottom-28 w-full h-px bg-slate-800/50 -z-10"></div>
            <div className="absolute bottom-52 w-full h-px bg-slate-800/50 -z-10"></div>
        </div>
    </div>
);
