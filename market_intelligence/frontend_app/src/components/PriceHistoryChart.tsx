import React, { useEffect, useState } from 'react';

export const PriceHistoryChart = () => {
    const [chartData, setChartData] = useState<any[]>([]);
    
    useEffect(() => {
        fetch('/api/scraped_data.json')
            .then(res => res.json())
            .then(data => {
                // Get a sample product to show (Samsung 12000 BTU)
                const samsungVisuar = data.visuar.find((p: any) => 
                    p.brand === 'SAMSUNG' && p.btu === 12000
                );
                const samsungGG = data.gg.find((p: any) => 
                    p.brand === 'SAMSUNG' && p.btu === 12000
                );
                
                if (samsungVisuar) {
                    setChartData([
                        { date: "Scraped", visuar: samsungVisuar.price, gg: samsungGG?.price || null }
                    ]);
                }
            });
    }, []);
    
    if (chartData.length === 0) {
        return (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl mt-6 p-6">
                <h3 className="text-xl font-semibold text-white mb-4">Comparación de Precios</h3>
                <p className="text-slate-400">No hay datos suficientes para mostrar gráfico histórico.</p>
            </div>
        );
    }
    
    const formatter = new Intl.NumberFormat('es-PY', { style: 'currency', currency: 'PYG', minimumFractionDigits: 0 });
    
    return (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl mt-6 p-6">
            <h3 className="text-xl font-semibold text-white mb-6">Comparación Actual: Visuar vs GG</h3>
            
            <div className="h-48 flex items-center justify-around gap-4">
                {chartData.map((point, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center max-w-xs">
                        <div className="w-full bg-slate-800 rounded-lg p-4">
                            <div className="mb-4">
                                <span className="text-xs text-indigo-400 font-medium block mb-1">Visuar</span>
                                <span className="text-xl font-bold text-white">{formatter.format(point.visuar)}</span>
                            </div>
                            <div className="border-t border-slate-700 pt-4">
                                <span className="text-xs text-blue-400 font-medium block mb-1">GG</span>
                                <span className="text-xl font-bold text-white">
                                    {point.gg ? formatter.format(point.gg) : 'N/A'}
                                </span>
                            </div>
                        </div>
                        <span className="text-xs text-slate-500 mt-2">{point.date}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};
