import React, { useState, useEffect } from 'react';

interface GGCatalogProduct {
    name: string;
    price: number;
    regular_price?: number | null;
    btu: number;
    is_inverter: boolean;
}

type GGCatalogData = Record<string, GGCatalogProduct[]>;

export const GGCatalog = () => {
    const [data, setData] = useState<GGCatalogData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch('/api/gg_ac_data.json');
                const result = await response.json();
                setData(result);
            } catch (error) {
                console.error("Error fetching GG AC data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center mt-6">
                <p className="text-slate-400">No se encontraron datos. Ejecuta el scraper The GG AC Scraper primero.</p>
            </div>
        );
    }

    const brands = Object.keys(data).sort();
    const totalProducts = Object.values(data).reduce((acc, current) => acc + current.length, 0);

    return (
        <div className="mt-6">
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-white">Catálogo Gonzalez Gimenez: Aires Acondicionados</h2>
                <p className="text-slate-400 mt-1">
                    Visualización cruda de {totalProducts} productos extraídos, agrupados por marca.
                </p>
            </div>

            <div className="grid grid-cols-1 gap-8">
                {brands.map((brand) => (
                    <div key={brand} className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
                        <div className="bg-slate-800/50 px-6 py-4 flex justify-between items-center border-b border-slate-700/50">
                            <h3 className="text-xl font-bold text-indigo-400 tracking-wide uppercase">{brand}</h3>
                            <span className="bg-slate-800 text-slate-300 text-xs font-semibold px-3 py-1 rounded-full">
                                {data[brand].length} SKUs
                            </span>
                        </div>

                        <div className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {data[brand].map((product, idx) => (
                                    <div key={idx} className="bg-slate-950/50 border border-slate-800 hover:border-indigo-500/50 transition-colors p-4 rounded-xl flex flex-col justify-between">
                                        <div>
                                            <h4 className="text-slate-200 font-medium text-sm leading-snug line-clamp-2" title={product.name}>
                                                {product.name}
                                            </h4>
                                            <div className="flex gap-2 mt-3">
                                                <span className="bg-indigo-500/10 text-indigo-400 text-xs px-2 py-0.5 rounded border border-indigo-500/20">
                                                    {product.btu} BTU
                                                </span>
                                                <span className={`text-xs px-2 py-0.5 rounded border ${product.is_inverter ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-slate-800 text-slate-400 border-slate-700'}`}>
                                                    {product.is_inverter ? 'INVERTER' : 'ON/OFF'}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="mt-4 pt-4 border-t border-slate-800/50 flex flex-col items-end">
                                            <div className="flex justify-between w-full items-center mb-1">
                                                <span className="text-xs text-slate-500">Precio Regular</span>
                                                <span className={`text-xs ${product.regular_price && product.regular_price > product.price ? 'text-slate-500 line-through' : 'text-slate-700'}`}>
                                                    {product.regular_price ? `Gs. ${product.regular_price.toLocaleString('es-PY')}` : '---'}
                                                </span>
                                            </div>
                                            <div className="flex justify-between w-full items-end">
                                                <span className="text-xs text-indigo-400 font-medium">Precio Final</span>
                                                <span className="text-lg font-bold text-white tabular-nums">
                                                    Gs. {product.price.toLocaleString('es-PY')}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
