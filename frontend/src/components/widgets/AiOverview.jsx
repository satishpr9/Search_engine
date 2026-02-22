import React, { useState, useRef, useEffect } from 'react';
import { Sparkle, PaperPlaneRight, CaretDown } from '@phosphor-icons/react';
import { marked } from 'marked';

export default function AiOverview({ query, results }) {
    const [summary, setSummary] = useState('');
    const [chatLog, setChatLog] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);
    const [hasOverflow, setHasOverflow] = useState(false);

    const contentRef = useRef(null);

    // Initial fetch for the "What is..." type queries
    useEffect(() => {
        let active = true;
        setSummary('');
        setIsExpanded(false);

        // Simulate streaming the initial summary
        const fetchAi = async () => {
            try {
                const context = results ? results.slice(0, 5).map(r => `Title: ${r.title}\nSnippet: ${r.snippet}`).join('\n\n') : '';
                const response = await fetch('/api/stream_ai', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: `Provide a summary of: ${query}`, context })
                });
                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                while (active) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const dataStr = line.substring(6);
                            if (dataStr === '[DONE]') {
                                break;
                            }
                            try {
                                const data = JSON.parse(dataStr);
                                if (data.text) {
                                    setSummary(prev => prev + data.text);
                                }
                            } catch (e) { }
                        }
                    }
                }
            } catch (err) {
                console.error(err);
            }
        };

        fetchAi();
        return () => { active = false; };
    }, [query, results]);

    // Check overflow for "Show more" button
    useEffect(() => {
        if (contentRef.current) {
            if (contentRef.current.scrollHeight > 180) {
                setHasOverflow(true);
            }
        }
    }, [summary]);

    const handleChatSubmit = async (e) => {
        e.preventDefault();
        if (!inputValue.trim() || isLoading) return;

        const userMsg = inputValue.trim();
        setInputValue('');
        setChatLog(prev => [...prev, { role: 'user', content: userMsg }]);

        setIsLoading(true);
        let currentBotReply = '';

        setChatLog(prev => [...prev, { role: 'ai', content: '' }]); // Placeholder

        try {
            const context = results ? results.slice(0, 5).map(r => `Title: ${r.title}\nSnippet: ${r.snippet}`).join('\n\n') : '';
            const response = await fetch('/api/stream_ai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userMsg, context })
            });
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6);
                        if (dataStr === '[DONE]') break;
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.text) {
                                currentBotReply += data.text;
                                setChatLog(prev => {
                                    const newLog = [...prev];
                                    newLog[newLog.length - 1].content = currentBotReply;
                                    return newLog;
                                });
                            }
                        } catch (e) { }
                    }
                }
            }
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    if (!summary && !isLoading) {
        // Only show if we actually generated something or are loading
        return null; /* In real Google, it shows a shimmer loader, we can keep it simple */
    }

    return (
        <div className="ai-overview-card">
            <div className="ai-header">
                <Sparkle weight="fill" />
                <h3>AI Overview</h3>
            </div>

            <div
                ref={contentRef}
                className={`ai-content ${isExpanded ? 'expanded' : ''}`}
                dangerouslySetInnerHTML={{ __html: marked.parse(summary || 'Generating...') }}
            />

            {hasOverflow && !isExpanded && (
                <button className="show-more-btn" onClick={() => setIsExpanded(true)}>
                    <CaretDown size={14} /> Show more
                </button>
            )}

            {chatLog.length > 0 && (
                <div className="ai-chat-thread">
                    {chatLog.map((msg, idx) => (
                        <div key={idx} className={`chat-bubble ${msg.role}`}>
                            <div dangerouslySetInnerHTML={{ __html: marked.parse(msg.content) }} />
                        </div>
                    ))}
                </div>
            )}

            <form className="ai-chat-form" onSubmit={handleChatSubmit} style={{ display: isExpanded ? 'flex' : (chatLog.length > 0 ? 'flex' : 'none') }}>
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Ask a follow-up question..."
                    disabled={isLoading}
                />
                <button type="submit" disabled={isLoading}>
                    <PaperPlaneRight weight="fill" />
                </button>
            </form>
        </div>
    );
}
