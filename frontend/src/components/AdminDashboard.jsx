import React, { useState, useEffect, useRef } from 'react';
import { Database, Pulse, HardDrives, Link } from '@phosphor-icons/react';
import '../index.css';

export default function AdminDashboard() {
    const [stats, setStats] = useState({ indexed_pages: 0, discovered_links: '0', db_size_mb: 0 });
    const [status, setStatus] = useState('connecting');
    const wsRef = useRef(null);

    useEffect(() => {
        // Connect to FastAPI WebSocket
        const wsUrl = `ws://${window.location.hostname}:8080/api/ws/admin`;

        const connectWs = () => {
            wsRef.current = new WebSocket(wsUrl);

            wsRef.current.onopen = () => setStatus('online');

            wsRef.current.onmessage = (event) => {
                try {
                    const liveData = JSON.parse(event.data);
                    setStats({
                        indexed_pages: liveData.indexed_pages,
                        discovered_links: liveData.discovered_links,
                        db_size_mb: liveData.db_size_mb
                    });
                } catch (e) {
                    console.error("Failed to parse WS data", e);
                }
            };

            wsRef.current.onclose = () => {
                setStatus('offline');
                setTimeout(connectWs, 3000); // Reconnect timer
            };
        };

        connectWs();

        return () => {
            if (wsRef.current) wsRef.current.close();
        };
    }, []);

    return (
        <div className="admin-dashboard">
            <header className="admin-header">
                <div className="admin-logo">
                    <Database weight="duotone" size={28} color="#1a73e8" />
                    <h2>Crawler Admin Console</h2>
                </div>
                <div className={`status-badge ${status}`}>
                    <span className="pulse-dot"></span>
                    {status === 'online' ? 'Live Connection' : 'Disconnected'}
                </div>
            </header>

            <main className="admin-grid">
                <div className="kpi-card">
                    <div className="kpi-icon blue">
                        <Pulse weight="fill" />
                    </div>
                    <div className="kpi-data">
                        <span className="kpi-label">Pages Indexed</span>
                        <span className="kpi-value">{stats.indexed_pages.toLocaleString()}</span>
                    </div>
                </div>

                <div className="kpi-card">
                    <div className="kpi-icon green">
                        <Link weight="fill" />
                    </div>
                    <div className="kpi-data">
                        <span className="kpi-label">Crawl Queue</span>
                        <span className="kpi-value">{typeof stats.discovered_links === 'number' ? stats.discovered_links.toLocaleString() : stats.discovered_links}</span>
                    </div>
                </div>

                <div className="kpi-card">
                    <div className="kpi-icon purple">
                        <HardDrives weight="fill" />
                    </div>
                    <div className="kpi-data">
                        <span className="kpi-label">Database Size</span>
                        <span className="kpi-value">{stats.db_size_mb} MB</span>
                    </div>
                </div>
            </main>
        </div>
    );
}
