import React from 'react';

export function ImageGridItem({ hit, onClick }) {
    return (
        <a href="#" className="image-grid-item" onClick={(e) => { e.preventDefault(); onClick(hit); }}>
            <div className="img-wrapper">
                <img src={hit.thumbnail_url} alt="" />
            </div>
            <div className="img-meta">
                <div className="img-source-wrap">
                    <span className="img-source-text">{new URL(hit.url).hostname}</span>
                </div>
                <div className="img-title" dangerouslySetInnerHTML={{ __html: hit.title || 'Untitled' }} />
            </div>
        </a>
    );
}

export function VideoGridItem({ hit, onClick }) {
    return (
        <a href="#" className="video-grid-item" onClick={(e) => { e.preventDefault(); onClick(hit); }}>
            <div className="video-thumb-wrapper">
                <img src={hit.thumbnail_url} alt="" />
                <div className="play-overlay">
                    <span>▶ Play</span>
                </div>
            </div>
            <div className="video-meta">
                <div className="video-title" dangerouslySetInnerHTML={{ __html: hit.title }} />
                <div className="video-source">{new URL(hit.url).hostname}</div>
            </div>
        </a>
    );
}

export function NewsListItem({ hit }) {
    return (
        <a href={hit.url} className="news-list-item">
            <div className="news-content-block">
                <div className="news-source-meta">{new URL(hit.url).hostname}</div>
                <div className="news-title" dangerouslySetInnerHTML={{ __html: hit.title }} />
                <div className="result-snippet" dangerouslySetInnerHTML={{ __html: hit.snippet }} style={{ marginTop: '8px' }} />
            </div>
            {hit.thumbnail_url && (
                <div className="news-thumb-block">
                    <img src={hit.thumbnail_url} alt="" />
                </div>
            )}
        </a>
    );
}

export function NewsCarouselItem({ hit, onClick }) {
    return (
        <a href="#" className="news-carousel-item" onClick={(e) => { e.preventDefault(); onClick(hit); }}>
            <div className="nc-thumb">
                <img src={hit.image || hit.thumbnail_url || ''} alt="" />
                <div className="nc-source-badge">{new URL(hit.url).hostname.replace('www.', '')}</div>
            </div>
            <div className="nc-content">
                <div className="nc-title" dangerouslySetInnerHTML={{ __html: hit.title }} />
                <div className="nc-meta">Related Image</div>
            </div>
        </a>
    );
}
