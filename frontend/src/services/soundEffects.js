const STORAGE_KEYS = {
  muted: "blackjack_sfx_muted",
  volume: "blackjack_sfx_volume",
};

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const randomRange = (min, max) => min + Math.random() * (max - min);

const SAMPLE_LIBRARY = {
  cardDeal: "/sounds/card-deal.wav",
  cardHit: "/sounds/card-hit.wav",
  cardStand: "/sounds/card-stand.wav",
  cardsShuffle: "/sounds/cards-shuffle.wav",
  chipPlace: "/sounds/chip-place.wav",
};

class SoundEffectsEngine {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.fxGain = null;
    this.compressor = null;
    this.noiseBuffer = null;
    this.unlocked = false;
    this.sampleBuffers = new Map();
    this.sampleLoading = null;
    this.convolver = null;
    this.reverbGain = null;

    this.muted = this._loadMuted();
    this.volume = this._loadVolume();
  }

  _loadMuted() {
    try {
      return window.localStorage.getItem(STORAGE_KEYS.muted) === "1";
    } catch {
      return false;
    }
  }

  _loadVolume() {
    try {
      const raw = Number(window.localStorage.getItem(STORAGE_KEYS.volume));
      if (Number.isFinite(raw)) return clamp(raw, 0, 100);
    } catch {
      // noop
    }
    return 72;
  }

  _persist() {
    try {
      window.localStorage.setItem(STORAGE_KEYS.muted, this.muted ? "1" : "0");
      window.localStorage.setItem(STORAGE_KEYS.volume, String(this.volume));
    } catch {
      // noop
    }
  }

  _ensureContext() {
    if (typeof window === "undefined") return null;
    if (this.ctx) return this.ctx;

    const AudioContextImpl = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextImpl) return null;

    this.ctx = new AudioContextImpl();

    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.value = 0;
    this.masterGain.connect(this.ctx.destination);

    this.compressor = this.ctx.createDynamicsCompressor();
    this.compressor.threshold.value = -16;
    this.compressor.knee.value = 24;
    this.compressor.ratio.value = 4;
    this.compressor.attack.value = 0.003;
    this.compressor.release.value = 0.2;
    this.compressor.connect(this.masterGain);

    this.fxGain = this.ctx.createGain();
    this.fxGain.gain.value = 1;
    this.fxGain.connect(this.compressor);

    this.convolver = this.ctx.createConvolver();
    this.convolver.buffer = this._createImpulseResponse(0.22, 2.4);
    this.reverbGain = this.ctx.createGain();
    this.reverbGain.gain.value = 0.2;
    this.reverbGain.connect(this.convolver);
    this.convolver.connect(this.compressor);

    this._applyMasterVolume(true);
    return this.ctx;
  }

  _createImpulseResponse(seconds = 0.22, decay = 2.4) {
    const length = Math.max(1, Math.floor(this.ctx.sampleRate * seconds));
    const impulse = this.ctx.createBuffer(2, length, this.ctx.sampleRate);
    for (let channel = 0; channel < 2; channel += 1) {
      const data = impulse.getChannelData(channel);
      for (let i = 0; i < length; i += 1) {
        const t = i / length;
        data[i] = (Math.random() * 2 - 1) * Math.pow(1 - t, decay);
      }
    }
    return impulse;
  }

  _toLinearGain() {
    if (this.muted) return 0;
    const normalized = clamp(this.volume / 100, 0, 1);
    return Math.pow(normalized, 1.35);
  }

  _applyMasterVolume(immediate = false) {
    if (!this.masterGain || !this.ctx) return;
    const target = this._toLinearGain();
    const now = this.ctx.currentTime;
    this.masterGain.gain.cancelScheduledValues(now);
    if (immediate) {
      this.masterGain.gain.setValueAtTime(target, now);
    } else {
      this.masterGain.gain.setTargetAtTime(target, now, 0.02);
    }
  }

  _sampleVolume(baseVolume = 1) {
    return clamp(baseVolume, 0, 1);
  }

  async _preloadSamples() {
    const ctx = this._ensureContext();
    if (!ctx || typeof window === "undefined") return;
    if (this.sampleLoading) {
      await this.sampleLoading;
      return;
    }

    this.sampleLoading = Promise.all(
      Object.entries(SAMPLE_LIBRARY).map(async ([key, src]) => {
        if (this.sampleBuffers.has(key)) return;
        try {
          const response = await fetch(src);
          const arr = await response.arrayBuffer();
          const buffer = await ctx.decodeAudioData(arr.slice(0));
          this.sampleBuffers.set(key, buffer);
        } catch {
          // Keep the app functional even if a sample fails to load.
        }
      }),
    );
    await this.sampleLoading;
  }

  _playSample(
    key,
    {
      delay = 0,
      volume = 1,
      playbackRate = 1,
      pan = 0,
      reverb = 0.18,
    } = {},
  ) {
    const ctx = this._ensureContext();
    if (!ctx || !this.unlocked || this.muted || !this.fxGain) return;
    const buffer = this.sampleBuffers.get(key);
    if (!buffer) return;

    const start = ctx.currentTime + Math.max(0, delay);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.playbackRate.setValueAtTime(playbackRate, start);

    const gainNode = ctx.createGain();
    gainNode.gain.setValueAtTime(this._sampleVolume(volume), start);

    const panner = ctx.createStereoPanner();
    panner.pan.setValueAtTime(clamp(pan, -1, 1), start);

    source.connect(gainNode);
    gainNode.connect(panner);
    panner.connect(this.fxGain);

    if (this.reverbGain) {
      const wet = ctx.createGain();
      wet.gain.setValueAtTime(clamp(reverb, 0, 0.7), start);
      panner.connect(wet);
      wet.connect(this.reverbGain);
    }

    source.start(start);
  }

  _ensureNoiseBuffer() {
    if (!this.ctx || this.noiseBuffer) return;
    const length = this.ctx.sampleRate * 2;
    this.noiseBuffer = this.ctx.createBuffer(1, length, this.ctx.sampleRate);
    const data = this.noiseBuffer.getChannelData(0);
    for (let i = 0; i < length; i += 1) {
      data[i] = randomRange(-1, 1);
    }
  }

  _tone({
    delay = 0,
    duration = 0.1,
    type = "sine",
    freq = 440,
    freqEnd = null,
    gain = 0.05,
    attack = 0.002,
    release = 0.06,
    pan = 0,
  }) {
    const ctx = this._ensureContext();
    if (!ctx || !this.unlocked || !this.fxGain) return;

    const start = ctx.currentTime + delay;
    const end = start + duration;

    const osc = ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, start);
    if (freqEnd != null) {
      osc.frequency.exponentialRampToValueAtTime(Math.max(40, freqEnd), end);
    }

    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0.0001, start);
    amp.gain.linearRampToValueAtTime(gain, start + attack);
    amp.gain.exponentialRampToValueAtTime(0.0001, end + release);

    const panner = ctx.createStereoPanner();
    panner.pan.setValueAtTime(clamp(pan, -1, 1), start);

    osc.connect(amp);
    amp.connect(panner);
    panner.connect(this.fxGain);

    osc.start(start);
    osc.stop(end + release + 0.02);
  }

  _noise({
    delay = 0,
    duration = 0.05,
    gain = 0.02,
    attack = 0.001,
    release = 0.05,
    filterType = "bandpass",
    filterFreq = 1600,
    filterQ = 0.8,
    pan = 0,
  }) {
    const ctx = this._ensureContext();
    if (!ctx || !this.unlocked || !this.fxGain) return;
    this._ensureNoiseBuffer();
    if (!this.noiseBuffer) return;

    const start = ctx.currentTime + delay;
    const end = start + duration;

    const source = ctx.createBufferSource();
    source.buffer = this.noiseBuffer;

    const filter = ctx.createBiquadFilter();
    filter.type = filterType;
    filter.frequency.setValueAtTime(filterFreq, start);
    filter.Q.value = filterQ;

    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0.0001, start);
    amp.gain.linearRampToValueAtTime(gain, start + attack);
    amp.gain.exponentialRampToValueAtTime(0.0001, end + release);

    const panner = ctx.createStereoPanner();
    panner.pan.setValueAtTime(clamp(pan, -1, 1), start);

    source.connect(filter);
    filter.connect(amp);
    amp.connect(panner);
    panner.connect(this.fxGain);

    source.start(start);
    source.stop(end + release + 0.02);
  }

  async unlock() {
    const ctx = this._ensureContext();
    if (!ctx) return;
    if (ctx.state === "suspended") {
      await ctx.resume();
    }
    this.unlocked = true;
    this._applyMasterVolume();
    await this._preloadSamples();
  }

  getSettings() {
    return { muted: this.muted, volume: this.volume };
  }

  setMuted(nextMuted) {
    this.muted = Boolean(nextMuted);
    this._persist();
    this._applyMasterVolume();
  }

  setVolume(nextVolume) {
    this.volume = clamp(Number(nextVolume) || 0, 0, 100);
    this._persist();
    this._applyMasterVolume();
  }

  playButton(delay = 0) {
    this._tone({
      delay,
      duration: 0.05,
      type: "triangle",
      freq: 1180,
      freqEnd: 740,
      gain: 0.045,
      pan: randomRange(-0.22, 0.22),
    });
  }

  playChip(delay = 0) {
    const pan = randomRange(-0.45, 0.45);
    this._playSample("chipPlace", {
      delay,
      volume: 0.62,
      playbackRate: randomRange(0.98, 1.03),
      pan,
      reverb: 0.08,
    });
  }

  playDealCard(delay = 0, accent = false) {
    this._playSample("cardDeal", {
      delay,
      volume: accent ? 1 : 0.84,
      playbackRate: randomRange(0.95, 1.08),
      pan: randomRange(-0.42, 0.42),
      reverb: 0.2,
    });
  }

  playDealSequence(cardCount = 4, interval = 0.085, startDelay = 0) {
    const safeCount = clamp(cardCount, 1, 10);
    for (let i = 0; i < safeCount; i += 1) {
      this.playDealCard(startDelay + i * interval, i === safeCount - 1);
    }
  }

  playHit() {
    this._playSample("cardHit", {
      delay: 0,
      volume: 1,
      playbackRate: randomRange(0.96, 1.05),
      pan: randomRange(-0.25, 0.25),
      reverb: 0.18,
    });
  }

  playStand() {
    this._playSample("cardStand", {
      delay: 0,
      volume: 0.92,
      playbackRate: randomRange(0.98, 1.03),
      pan: randomRange(-0.18, 0.18),
      reverb: 0.22,
    });
  }

  playSplit() {
    this.playChip(0);
    this.playDealCard(0.06);
    this.playDealCard(0.14, true);
  }

  playDouble() {
    this.playChip(0);
    this.playChip(0.035);
    this._playSample("cardHit", {
      delay: 0.1,
      volume: 1.02,
      playbackRate: randomRange(0.98, 1.05),
      pan: randomRange(-0.22, 0.22),
      reverb: 0.2,
    });
  }

  playShuffle() {
    this._playSample("cardsShuffle", {
      delay: 0,
      volume: 0.88,
      playbackRate: randomRange(0.96, 1.03),
      pan: randomRange(-0.15, 0.15),
      reverb: 0.24,
    });
  }

  playWin() {
    [523.25, 659.25, 783.99, 1046.5].forEach((note, idx) => {
      this._tone({
        delay: idx * 0.08,
        duration: 0.18,
        type: "triangle",
        freq: note,
        freqEnd: note * 1.01,
        gain: 0.055,
      });
    });
  }

  playBlackjack() {
    [392.0, 523.25, 659.25, 783.99, 1046.5].forEach((note, idx) => {
      this._tone({
        delay: idx * 0.07,
        duration: 0.2,
        type: "sine",
        freq: note,
        freqEnd: note * 1.005,
        gain: 0.062,
      });
    });
    this._noise({
      delay: 0.2,
      duration: 0.18,
      gain: 0.014,
      filterType: "highpass",
      filterFreq: 2800,
      filterQ: 0.8,
    });
  }

  playPush() {
    this._tone({
      delay: 0,
      duration: 0.14,
      type: "triangle",
      freq: 392,
      freqEnd: 392,
      gain: 0.04,
    });
    this._tone({
      delay: 0.14,
      duration: 0.14,
      type: "triangle",
      freq: 392,
      freqEnd: 392,
      gain: 0.036,
    });
  }

  playLose() {
    [330, 247, 196].forEach((note, idx) => {
      this._tone({
        delay: idx * 0.1,
        duration: 0.17,
        type: "sawtooth",
        freq: note,
        freqEnd: note * 0.92,
        gain: 0.04,
      });
    });
  }

  playError() {
    this._tone({
      delay: 0,
      duration: 0.09,
      type: "square",
      freq: 170,
      freqEnd: 120,
      gain: 0.033,
    });
    this._tone({
      delay: 0.08,
      duration: 0.09,
      type: "square",
      freq: 170,
      freqEnd: 120,
      gain: 0.03,
    });
  }
}

export const soundFX = new SoundEffectsEngine();
