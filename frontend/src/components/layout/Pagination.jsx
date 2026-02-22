import React from 'react';
import { CaretLeft, CaretRight } from '@phosphor-icons/react';

export default function Pagination({ page, totalPages, onPageChange }) {
    if (totalPages <= 1) return null;

    const startPage = Math.max(1, page - 4);
    const endPage = Math.min(totalPages, startPage + 9);

    const pages = [];
    for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
    }

    return (
        <div className="pagination-controls" style={{ display: 'flex' }}>
            <button
                className="page-btn"
                onClick={() => onPageChange(page - 1)}
                disabled={page === 1}
            >
                <CaretLeft size={16} /> Previous
            </button>

            <div className="page-numbers">
                {pages.map(p => (
                    <div
                        key={p}
                        className={`pg-num ${p === page ? 'active' : ''}`}
                        onClick={() => onPageChange(p)}
                    >
                        {p}
                    </div>
                ))}
            </div>

            <button
                className="page-btn"
                onClick={() => onPageChange(page + 1)}
                disabled={page === totalPages}
            >
                Next <CaretRight size={16} />
            </button>
        </div>
    );
}
