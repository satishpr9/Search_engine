import React, { useState } from 'react';
import { MagnifyingGlass, X, ArrowRight, Microphone } from '@phosphor-icons/react';
import { useVoiceSearch } from '../../hooks/useVoiceSearch';

export default function Header({ query, setQuery, onSearch, hasSearched, goHome, suggestions, setSuggestions }) {
    const [isFocused, setIsFocused] = useState(false);

    const onVoiceSubmit = (transcript) => {
        setQuery(transcript);
        onSearch(transcript);
        setSuggestions([]);
    };

    const { isListening, toggleListening, hasSupport } = useVoiceSearch(onVoiceSubmit);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (query.trim()) {
            onSearch(query.trim());
            setSuggestions([]); // hide autocomplete
        }
    };

    const handleSuggestionClick = (sug) => {
        setQuery(sug);
        onSearch(sug);
        setSuggestions([]);
    };

    return (
        <header className="masthead">
            <div className="logo" onClick={goHome} aria-label="Icro Home" style={hasSearched ? { cursor: 'pointer' } : {}}>
                <span className="logo-text">Icro</span>
            </div>

            <div className="search-wrapper">
                <form
                    className={`search-form ${isFocused ? 'focused' : ''}`}
                    onSubmit={handleSubmit}
                >
                    <MagnifyingGlass size={20} weight="regular" className="search-icon" />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder=""
                        autoComplete="off"
                        spellCheck="false"
                        autoFocus
                        onFocus={() => setIsFocused(true)}
                        onBlur={() => setTimeout(() => setIsFocused(false), 200)} // delay to allow clicks
                    />

                    {query && (
                        <button type="button" className="icon-btn" onClick={() => setQuery('')} aria-label="Clear Search">
                            <X size={20} />
                        </button>
                    )}

                    {hasSupport && (
                        <button
                            type="button"
                            className={`icon-btn mic-btn ${isListening ? 'listening' : ''}`}
                            onClick={toggleListening}
                            aria-label="Voice Search"
                        >
                            <Microphone size={20} weight={isListening ? "fill" : "regular"} className={isListening ? 'listening-icon' : ''} />
                        </button>
                    )}

                    <div className="divider"></div>

                    <button type="submit" className="icon-btn submit-btn" aria-label="Search">
                        <ArrowRight size={20} />
                    </button>
                </form>

                {/* Autocomplete Dropdown */}
                {suggestions.length > 0 && isFocused && (
                    <div className="autocomplete-box active">
                        {suggestions.map((sug, idx) => (
                            <div
                                key={idx}
                                className="suggestion-item"
                                onMouseDown={() => handleSuggestionClick(sug)} // mousedown fires before blur
                            >
                                <MagnifyingGlass size={16} /> {sug}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </header>
    );
}
