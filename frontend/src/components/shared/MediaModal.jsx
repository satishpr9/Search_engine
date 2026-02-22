import React from 'react';
import { X, ArrowUpRight } from '@phosphor-icons/react';

export default function MediaModal({ isOpen, onClose, mediaSource, mediaType, metaTitle, metaUrl }) {
    if (!isOpen) return null;

    return (
        <div className="media-modal active">
            <div className="media-modal-backdrop" onClick={onClose}></div>
            <div className="media-modal-content">
                <button className="icon-btn media-modal-close" onClick={onClose}>
                    <X size={32} />
                </button>
                <div className="media-modal-body">
                    {mediaType === 'image' && <img src={mediaSource} alt="Media full view" />}
                    {mediaType === 'video' && <iframe src={mediaSource} allowFullScreen></iframe>}
                </div>

                {(metaTitle || metaUrl) && (
                    <div className="media-modal-meta">
                        <div>
                            <div className="modal-title">{metaTitle}</div>
                            <div className="modal-source">{new URL(metaUrl).hostname}</div>
                        </div>
                        <a href={metaUrl} target="_blank" rel="noreferrer" className="modal-link">
                            Visit Site <ArrowUpRight size={16} style={{ verticalAlign: 'middle' }} />
                        </a>
                    </div>
                )}
            </div>
        </div>
    );
}
