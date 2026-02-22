import React from 'react';
import { MagnifyingGlass, Image, VideoCamera, Newspaper } from '@phosphor-icons/react';

export default function SearchTabs({ activeTab, onTabChange }) {
    const tabs = [
        { id: 'all', label: 'All', icon: <MagnifyingGlass size={18} /> },
        { id: 'images', label: 'Images', icon: <Image size={18} /> },
        { id: 'videos', label: 'Videos', icon: <VideoCamera size={18} /> },
        { id: 'news', label: 'News', icon: <Newspaper size={18} /> },
    ];

    return (
        <div className="search-tabs">
            {tabs.map(tab => (
                <a
                    key={tab.id}
                    href="#"
                    className={`search-tab ${activeTab === tab.id ? 'active' : ''}`}
                    onClick={(e) => {
                        e.preventDefault();
                        onTabChange(tab.id);
                    }}
                >
                    {tab.icon} {tab.label}
                </a>
            ))}
        </div>
    );
}
