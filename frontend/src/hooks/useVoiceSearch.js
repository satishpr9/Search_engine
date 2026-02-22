import { useState, useEffect, useCallback } from 'react';

export function useVoiceSearch(onResultSubmit) {
    const [isListening, setIsListening] = useState(false);
    const [recognition, setRecognition] = useState(null);
    const [transcript, setTranscript] = useState('');

    useEffect(() => {
        // Initialize Speech Recognition API
        if (typeof window !== 'undefined') {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (SpeechRecognition) {
                const rec = new SpeechRecognition();
                rec.continuous = false;
                rec.interimResults = true;
                rec.lang = 'en-US';

                rec.onresult = (event) => {
                    let currentTranscript = '';
                    for (let i = event.resultIndex; i < event.results.length; ++i) {
                        currentTranscript += event.results[i][0].transcript;
                    }
                    setTranscript(currentTranscript);

                    // If the user stopped speaking and the result is final
                    if (event.results[0].isFinal) {
                        rec.stop();
                        setIsListening(false);
                        if (onResultSubmit && currentTranscript.trim()) {
                            onResultSubmit(currentTranscript.trim());
                        }
                    }
                };

                rec.onerror = (event) => {
                    console.error('Speech recognition error', event.error);
                    setIsListening(false);
                };

                rec.onend = () => {
                    setIsListening(false);
                };

                setRecognition(rec);
            } else {
                console.warn('Speech Recognition API not supported in this browser.');
            }
        }
    }, [onResultSubmit]);

    const startListening = useCallback(() => {
        if (recognition && !isListening) {
            setTranscript('');
            setIsListening(true);
            try {
                recognition.start();
            } catch (e) {
                console.error(e);
            }
        }
    }, [recognition, isListening]);

    const stopListening = useCallback(() => {
        if (recognition && isListening) {
            recognition.stop();
            setIsListening(false);
        }
    }, [recognition, isListening]);

    const toggleListening = useCallback(() => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    }, [isListening, startListening, stopListening]);

    return {
        isListening,
        transcript,
        toggleListening,
        hasSupport: !!recognition
    };
}
