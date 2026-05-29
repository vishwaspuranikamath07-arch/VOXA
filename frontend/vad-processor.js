/**
 * frontend/vad-processor.js
 * 
 * AudioWorkletProcessor for Voice Activity Detection (VAD).
 * Runs natively in the browser's audio thread to calculate RMS energy 
 * without blocking the main UI thread.
 */

class VADProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.threshold = 0.01;      // Energy threshold for speech
    this.speechFrames = 0;      // Consecutive frames above threshold
    this.silenceFrames = 0;     // Consecutive frames below threshold
    this.isSpeaking = false;
    
    // ~100ms = ~34 frames at 128 samples / 44100Hz
    this.minSpeechFrames = 15;
    // ~1500ms = ~516 frames
    this.minSilenceFrames = 516;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0];
    let sumSquares = 0;
    
    for (let i = 0; i < channelData.length; i++) {
      sumSquares += channelData[i] * channelData[i];
    }
    
    const rms = Math.sqrt(sumSquares / channelData.length);
    const isLoud = rms > this.threshold;

    if (isLoud) {
      this.speechFrames++;
      this.silenceFrames = 0;
      
      if (!this.isSpeaking && this.speechFrames >= this.minSpeechFrames) {
        this.isSpeaking = true;
        this.port.postMessage({ type: 'speech_start', rms });
      }
    } else {
      this.silenceFrames++;
      this.speechFrames = 0;
      
      if (this.isSpeaking && this.silenceFrames >= this.minSilenceFrames) {
        this.isSpeaking = false;
        this.port.postMessage({ type: 'speech_end', rms });
      }
    }

    // Send continuous volume info every ~50ms for UI visualization
    // 1 frame = 128 samples. At 44.1kHz, 50ms is ~17 frames.
    if (this.silenceFrames % 17 === 0 || this.speechFrames % 17 === 0) {
        this.port.postMessage({ type: 'volume', rms });
    }

    return true; // Keep processor alive
  }
}

registerProcessor('vad-processor', VADProcessor);
