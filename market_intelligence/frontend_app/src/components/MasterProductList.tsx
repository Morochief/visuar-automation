import React, { useState } from 'react';

export const MasterProductList = ({ products }) => {
    const [expandedRow, setExpandedRow] = useState(null);

    const getMatchBadge = (level, color) => {
        const colors = {
            green: 'bg-emerald-900/30 text-emerald-400 border-emerald-500/50',
            yellow: 'bg-amber-900/30 text-amber-400 border-amber-500/50',
            red: 'bg-rose-900/30 text-rose-400 border-rose-500/50'
        };
        return colors[color] || colors.red;
    };

    return (
        <div className="bg-white shadow rounded-lg border border-gray-200 mt-6 overflow-hidden">
            <table className="w-full text-left">
                <thead className="bg-slate-50 text-slate-700 text-sm border-b">
                    <tr>
                        <th className="p-4">SKU Maestro (Reference)</th>
                        <th className="p-4">Match</th>
                        <th className="p-4">Visuar</th>
                        <th className="p-4">Competidor</th>
                    </tr>
                </thead>
                <tbody>
                    {products.map(product => (
                        <React.Fragment key={product.id}>
                            <tr
                                className="hover:bg-blue-50 cursor-pointer border-b transition-colors"
                                onClick={() => setExpandedRow(expandedRow === product.id ? null : product.id)}
                            >
                                <td className="p-4 font-semibold text-slate-900">{product.master_name}</td>
                                <td className="p-4">
                                    {product.match_percentage ? (
                                        <span className={`px-2 py-1 rounded-full text-xs font-bold border ${getMatchBadge(product.match_level, product.match_color)}`}>
                                            {product.match_label} ({product.match_percentage}%)
                                        </span>
                                    ) : (
                                        <span className="text-slate-400">-</span>
                                    )}
                                </td>
                                <td className="p-4 font-bold text-slate-700">Gs. {product.visuar_price}</td>
                                <td className="p-4">
                                    {product.gg_price ? (
                                        <div className="flex flex-col">
                                            <span className="text-rose-600 font-bold">
                                                Gs. {product.gg_price?.toLocaleString('es-PY')} ({product.diff_percent}%)
                                            </span>
                                            <span className="text-xs text-slate-500">{product.best_competitor}</span>
                                        </div>
                                    ) : (
                                        <span className="text-slate-400">Sin datos</span>
                                    )}
                                </td>
                            </tr>

                            {/* Expandible de Competidores ("El Quirófano") */}
                            {expandedRow === product.id && (
                                <tr className="bg-slate-50 border-b">
                                    <td colSpan={3} className="p-6">
                                        <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">Competencia Mapeada</h4>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                            {product.competitors.map((comp, idx) => (
                                                <div key={idx} className="bg-white p-4 rounded border shadow-sm flex flex-col justify-between">
                                                    <div className="flex justify-between items-start mb-2">
                                                        <span className="font-bold text-slate-800">{comp.name}</span>
                                                        <span className={`text-xs px-2 py-1 rounded-full ${comp.diff > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                                            {comp.diff > 0 ? '+' : ''}{comp.diff}%
                                                        </span>
                                                    </div>
                                                    <div className="text-lg font-bold mb-2">Gs. {comp.price}</div>
                                                    <div className="text-xs text-slate-400 border-t pt-2 mt-auto">
                                                        Nombre web: "{comp.raw_name}"
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </React.Fragment>
                    ))}
                </tbody>
            </table>
        </div>
    );
};
