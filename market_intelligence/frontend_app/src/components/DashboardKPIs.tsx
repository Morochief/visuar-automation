import React from 'react';
import { TrendingDown, TrendingUp } from 'lucide-react';

export const DashboardKPIs = () => (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-slate-900 border-t-4 border-indigo-500 border-x border-b border-slate-800 p-6 rounded-2xl rounded-t-none shadow-xl">
            <p className="text-slate-400 font-medium">Impacto Estimado en Margen</p>
            <h3 className="text-3xl font-bold text-white mt-2">18.5%</h3>
            <div className="mt-4 flex items-center text-rose-400 bg-rose-500/10 w-fit px-2 py-1 rounded text-xs font-semibold">
                <TrendingDown size={14} className="mr-1" />
                -2.1% (Guerra de precios vs Nissei)
            </div>
        </div>

        <div className="bg-slate-900 border-t-4 border-rose-500 border-x border-b border-slate-800 p-6 rounded-2xl rounded-t-none shadow-xl">
            <p className="text-slate-400 font-medium">Fugas de Competitividad (Visuar más caro)</p>
            <h3 className="text-3xl font-bold text-white mt-2">42 SKUs</h3>
            <div className="mt-4 flex items-center text-emerald-400 bg-emerald-500/10 w-fit px-2 py-1 rounded text-xs font-semibold">
                <TrendingUp size={14} className="mr-1" />
                +12 Alertas esta semana
            </div>
        </div>

        <div className="bg-slate-900 border-t-4 border-emerald-500 border-x border-b border-slate-800 p-6 rounded-2xl rounded-t-none shadow-xl">
            <p className="text-slate-400 font-medium">Predador del Mercado (Más Agresivo)</p>
            <h3 className="text-3xl font-bold text-white mt-2">Bristol</h3>
            <div className="mt-4 text-xs text-slate-500 font-medium">
                Bate el precio de Visuar en un 65% del line-up Samsung.
            </div>
        </div>
    </div>
);
