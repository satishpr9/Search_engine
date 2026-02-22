import React from 'react';

// Common Google URL format logic
function getFavicon(urlStr) {
    try {
        const url = new URL(urlStr);
        return `https://www.google.com/s2/favicons?sz=64&domain_url=${url.origin}`;
    } catch {
        return 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZD0iTTEyIDJDNi40OCAyIDIgNi40OCAyIDEyczQuNDggMTAgMTAgMTAgMTAtNC40OCAxMC0xMFMxNy41MiAyIDEyIDJ6bS0xIDE3LjVjLTMuMzEtLjU1LTUuOTItMy4xNS02LjQ4LTYuNUgxMXY2LjV6bTAtOEg0LjUyQyUuMDYgMTAuMzUgNi41NSA3LjgxIDEwIDYuNXY0Ljk5em0yLTQuOTljMy40NSAxLjMxIDUuOTQgMy44NSA2LjQ4IDYuMUgxM1Y2LjV6bTAgOEgxMy4wMnYtN2wxLjk5LjAyQzE0Ljc1IDEwLjM0IDE0LjMgNy44MiAxNS4zMSA2LjV6bTAgOGMxLjAyLS45NCAxLjgyLTIuMTUgMi4yOS0zLjVoLTIuMjl2My41em0tMiAwdi0zLjVoLTIuMjlDNC4xOCAxNS4zNSA0Ljk4IDE2LjU2IDYgMTcuNXoiLz48L3N2Zz4=';
    }
}

function getDisplayUrl(urlStr) {
    try {
        const url = new URL(urlStr);
        let pathParts = url.pathname.split('/').filter(p => p.length > 0);
        let breadcrumb = url.origin;
        if (pathParts.length > 0) {
            breadcrumb += ' › ' + pathParts[0];
        }

        let siteName = url.hostname.replace('www.', '');
        const nameParts = siteName.split('.');
        if (nameParts.length > 1) {
            siteName = nameParts[nameParts.length - 2];
            siteName = siteName.charAt(0).toUpperCase() + siteName.slice(1);
        }

        return { siteName, breadcrumb };
    } catch {
        return { siteName: urlStr.substring(0, 30), breadcrumb: urlStr };
    }
}

export default function ResultCard({ hit }) {
    const { siteName, breadcrumb } = getDisplayUrl(hit.url);
    const favicon = getFavicon(hit.url);

    // dangerouslySetInnerHTML is required because Whoosh hilights search terms with <b> tags
    return (
        <div className="result-card">
            <div className="result-content-container">

                <div className="result-text-block">
                    <div className="result-url-group">
                        <img className="result-favicon" src={favicon} alt="" />
                        <div className="result-url-text-wrap">
                            <span className="url-site-name">{siteName}</span>
                            <span className="url-breadcrumb">{breadcrumb}</span>
                        </div>
                    </div>

                    <a href={hit.url} className="result-title">
                        <h3 dangerouslySetInnerHTML={{ __html: hit.title || 'Untitled Page' }} />
                    </a>

                    <p className="result-snippet" dangerouslySetInnerHTML={{ __html: hit.snippet || 'No snippet available.' }} />
                </div>

                {hit.thumbnail_url && (
                    <div className="result-thumb-container">
                        <img src={hit.thumbnail_url} alt="" />
                    </div>
                )}
            </div>
        </div>
    );
}
