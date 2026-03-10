import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

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

    const getStatusColor = (diffPercent) => {
        if (diffPercent === null || diffPercent === 0) return 'text-slate-400';
        // Positive diff = GG more expensive = WIN for Visuar
        return diffPercent > 0 ? 'text-emerald-400' : 'text-rose-400';
    };

    const formatter = new Intl.NumberFormat('es-PY', { minimumFractionDigits: 0 });

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl mt-6 overflow-hidden">
            <div className="p-5 border-b border-slate-800">
                <h3 className="text-lg font-semibold text-white">Tabla de Productos Maestros</h3>
                <p className="text-slate-500 text-sm mt-1">{products.length} productos analizados</p>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="bg-slate-950 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-800">
                        <tr>
                            <th className="p-4 w-8"></th>
                            <th className="p-4">Producto</th>
                            <th className="p-4 text-center">Match</th>
                            <th className="p-4 text-right">Visuar</th>
                            <th className="p-4 text-right">Costo V.</th>
                            <th className="p-4 text-right">Rentab.</th>
                            <th className="p-4 text-right">GG</th>
                            <th className="p-4 text-right">M. Competitivo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {products.map(product => (
                            <React.Fragment key={product.id}>
                                <tr
                                    className="hover:bg-slate-800/50 cursor-pointer border-b border-slate-800/50 transition-colors"
                                    onClick={() => setExpandedRow(expandedRow === product.id ? null : product.id)}
                                >
                                    <td className="p-4 text-slate-500">
                                        {expandedRow === product.id
                                            ? <ChevronDown size={14} />
                                            : <ChevronRight size={14} />
                                        }
                                    </td>
                                    <td className="p-4">
                                        <span className="font-medium text-white">{product.master_name}</span>
                                    </td>
                                    <td className="p-4 text-center">
                                        {product.match_percentage ? (
                                            <span className={`px-2 py-1 rounded-full text-xs font-bold border ${getMatchBadge(product.match_level, product.match_color)}`}>
                                                {product.match_label} ({product.match_percentage}%)
                                            </span>
                                        ) : (
                                            <span className="text-slate-600">-</span>
                                        )}
                                    </td>
                                    <td className="p-4 text-right">
                                        <span className="font-bold text-indigo-400">Gs. {product.visuar_price}</span>
                                    </td>
                                    <td className="p-4 text-right text-slate-400">
                                        {product.internal_cost ? `Gs. ${formatter.format(product.internal_cost)}` : '-'}
                                    </td>
                                    <td className="p-4 text-right">
                                        {product.real_margin_percent !== null && product.real_margin_percent !== undefined ? (
                                            <span className={`font-bold ${product.real_margin_percent > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                                {product.real_margin_percent > 0 ? '+' : ''}{product.real_margin_percent.toFixed(1)}%
                                            </span>
                                        ) : '-'}
                                    </td>
                                    <td className="p-4 text-right">
                                        {product.gg_price ? (
                                            <span className="font-bold text-blue-400">
                                                Gs. {formatter.format(product.gg_price)}
                                            </span>
                                        ) : (
                                            <span className="text-slate-600">Sin datos</span>
                                        )}
                                    </td>
                                    <td className="p-4 text-right">
                                        {product.diff_percent !== null && product.diff_percent !== 0 ? (
                                            <span className={`font-bold ${getStatusColor(product.diff_percent)}`}>
                                                {product.diff_percent > 0 ? '+' : ''}{product.diff_percent.toFixed(1)}%
                                            </span>
                                        ) : (
                                            <span className="text-slate-600">-</span>
                                        )}
                                    </td>
                                </tr>

                                {/* Expandible */}
                                {expandedRow === product.id && (
                                    <tr className="bg-slate-950 border-b border-slate-800">
                                        <td colSpan={8} className="p-6">
                                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Detalle de Competencia</h4>
                                            {product.competitors.length > 0 ? (
                                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                                    {product.competitors.map((comp, idx) => (
                                                        <div key={idx} className="bg-slate-900 p-4 rounded-lg border border-slate-800 flex flex-col justify-between">
                                                            <div className="flex justify-between items-start mb-2">
                                                                <span className="font-bold text-white text-sm">{comp.name}</span>
                                                                <span className={`text-xs px-2 py-1 rounded-full ${comp.diff > 0
                                                                    ? 'bg-emerald-900/30 text-emerald-400'
                                                                    : 'bg-rose-900/30 text-rose-400'
                                                                    }`}>
                                                                    {comp.diff > 0 ? '+' : ''}{comp.diff}%
                                                                </span>
                                                            </div>
                                                            <div className="text-lg font-bold text-white mb-2">Gs. {comp.price}</div>
                                                            <div className="text-xs text-slate-500 border-t border-slate-800 pt-2 mt-auto">
                                                                Web: "{comp.raw_name}"
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <p className="text-slate-500 text-sm">No hay competidores mapeados para este producto.</p>
                                            )}
                                        </td>
                                    </tr>
                                )}
                            </React.Fragment>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
