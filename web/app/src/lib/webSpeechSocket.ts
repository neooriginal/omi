import { TranscriptSegment } from './transcriptionSocket';

export interface WebSpeechSocketOptions {
    onSegment: (segment: TranscriptSegment) => void;
    onError: (error: string) => void;
    onConnected: () => void;
    onDisconnected: () => void;
    language?: string;
}

export class WebSpeechSocket {
    // @ts-ignore - Global type missing
    private recognition: any | null = null;
    private isListening = false;
    private options: WebSpeechSocketOptions;
    private currentSegmentId: string | null = null;
    private lastFinalTimestamp: number = 0;

    constructor(options: WebSpeechSocketOptions) {
        this.options = options;
    }

    async connect(): Promise<void> {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            this.options.onError('Web Speech API is not supported in this browser');
            return;
        }

        // @ts-ignore - SpeechRecognition types might not be fully available in all envs
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();

        if (this.recognition) {
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            // Map omi language codes to web speech locales if needed, but standard iso codes usually work
            this.recognition.lang = this.options.language || 'en-US';

            this.recognition.onstart = () => {
                this.isListening = true;
                this.options.onConnected();
            };

            this.recognition.onend = () => {
                if (this.isListening) {
                    // Refresh recognition instance on error/timeout if continuous
                    try {
                        this.recognition?.start();
                    } catch (e) {
                        // ignore
                    }
                } else {
                    this.options.onDisconnected();
                }
            };

            this.recognition.onerror = (event: any) => {
                // Ignore 'no-speech' errors as they just mean silence
                if (event.error === 'no-speech') return;

                console.error('Speech recognition error', event.error);
                if (event.error === 'not-allowed') {
                    this.options.onError('Microphone permission denied');
                    this.disconnect();
                }
            };

            this.recognition.onresult = (event: any) => {
                const result = event.results[event.results.length - 1];
                const transcript = result[0].transcript;
                const isFinal = result.isFinal;

                if (!transcript.trim()) return;

                // If we don't have a current segment ID or the previous one was finalized, create a new one
                if (!this.currentSegmentId) {
                    this.currentSegmentId = `web-speech-${Date.now()}`;
                }

                this.options.onSegment({
                    id: this.currentSegmentId,
                    text: transcript,
                    speaker: 0,
                    isUser: true,
                    timestamp: Date.now(),
                    isFinal: isFinal,
                });

                if (isFinal) {
                    this.currentSegmentId = null;
                }
            };

            this.recognition.start();
        }
    }

    // No-op for Web Speech API
    sendAudio(pcmData: Int16Array): void {
    }

    disconnect(): void {
        this.isListening = false;
        if (this.recognition) {
            this.recognition.stop();
            this.recognition = null;
        }
    }
}

export function createWebSpeechSocket(options: WebSpeechSocketOptions): WebSpeechSocket {
    return new WebSpeechSocket(options);
}
