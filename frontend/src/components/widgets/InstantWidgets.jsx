import React from 'react';

export default function InstantWidgets({ widget }) {
    if (!widget) return null;

    if (widget.type === 'calculator') {
        return (
            <div className="instant-widget-card">
                <div className="widget-calc-expr">{widget.expression} =</div>
                <div className="widget-calc-res">{widget.result}</div>
            </div>
        );
    }

    if (widget.type === 'weather') {
        return (
            <div className="instant-widget-card">
                <div className="widget-weather-header">
                    {/* We rely on Phosphor defaults or skip icon since we don't have dynamic mapped icons easily */}
                    <div className="widget-weather-temp">{widget.temperature}</div>
                    <div className="widget-weather-details">
                        <div className="widget-weather-cond">{widget.condition}</div>
                        <div className="widget-weather-loc">{widget.location}</div>
                    </div>
                </div>
            </div>
        );
    }

    return null;
}
