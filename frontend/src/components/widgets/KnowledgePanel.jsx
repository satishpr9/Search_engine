import React, { useRef } from 'react';
import { CaretLeft, CaretRight, ArrowSquareOut } from '@phosphor-icons/react';

export default function KnowledgePanel({ kp }) {
    if (!kp) return null;

    const scrollRef = useRef(null);

    const scrollLeft = () => {
        if (scrollRef.current) {
            scrollRef.current.scrollBy({ left: -300, behavior: 'smooth' });
        }
    };

    const scrollRight = () => {
        if (scrollRef.current) {
            scrollRef.current.scrollBy({ left: 300, behavior: 'smooth' });
        }
    };

    return (
        <div className="knowledge-panel fade-in">
            {/* 1. Related Entities Carousel (Things to do / Related) */}
            {kp.related_entities && kp.related_entities.length > 0 && (
                <div className="kp-related-section">
                    <h3 className="kp-section-title">Related entities</h3>
                    <div className="kp-carousel-container">
                        <button className="kp-carousel-btn left" onClick={scrollLeft} aria-label="Scroll left">
                            <CaretLeft weight="bold" />
                        </button>
                        <div className="kp-carousel" ref={scrollRef}>
                            {kp.related_entities.map((entity, i) => (
                                <a key={i} href={entity.url} target="_blank" rel="noopener noreferrer" className="kp-related-card">
                                    <div className="kp-card-img-container">
                                        {entity.image_url ? (
                                            <img src={entity.image_url} alt={entity.title} loading="lazy" />
                                        ) : (
                                            <div className="kp-card-no-img">No Image</div>
                                        )}
                                    </div>
                                    <div className="kp-card-content">
                                        <div className="kp-card-title">{entity.title}</div>
                                        {entity.description && (
                                            <div className="kp-card-desc">{entity.description}</div>
                                        )}
                                    </div>
                                </a>
                            ))}
                        </div>
                        <button className="kp-carousel-btn right" onClick={scrollRight} aria-label="Scroll right">
                            <CaretRight weight="bold" />
                        </button>
                    </div>
                </div>
            )}

            {/* 2. Main About Section */}
            <div className="kp-main-card">
                <div className="kp-header">
                    <h2 className="kp-title">{kp.title}</h2>
                </div>

                {kp.image_url && (
                    <div className="kp-hero-image">
                        <img src={kp.image_url} alt={kp.title} />
                    </div>
                )}

                <div className="kp-about-section">
                    <h3 className="kp-section-title">About</h3>
                    {kp.extract && (
                        <p className="kp-extract">
                            {kp.extract}{' '}
                            {kp.url && (
                                <a href={kp.url} target="_blank" rel="noopener noreferrer" className="kp-wiki-link">
                                    Wikipedia
                                </a>
                            )}
                        </p>
                    )}

                    {kp.facts && Object.keys(kp.facts).length > 0 && (
                        <div className="kp-facts-list">
                            {Object.entries(kp.facts).map(([key, val]) => (
                                <div className="kp-fact-item" key={key}>
                                    <span className="kp-fact-label">{key}: </span>
                                    <span className="kp-fact-value">{val}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
