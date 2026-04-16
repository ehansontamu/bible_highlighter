const typedInput = document.getElementById("typedInput");
const transcriptText = document.getElementById("transcriptText");
const keywordChips = document.getElementById("keywordChips");
const resultMeta = document.getElementById("resultMeta");
const wallMeta = document.getElementById("wallMeta");
const chapterWall = document.getElementById("chapterWall");
const micToggle = document.getElementById("micToggle");
const micReset = document.getElementById("micReset");
const micStatus = document.getElementById("micStatus");
const startupStatus = document.getElementById("startupStatus");
const audioFileInput = document.getElementById("audioFileInput");
const audioPlayer = document.getElementById("audioPlayer");
const fileStatus = document.getElementById("fileStatus");
const windowStatus = document.getElementById("windowStatus");

let typedTimer = null;
let sessionId = null;
let mediaStream = null;
let audioContext = null;
let processor = null;
let source = null;
let flushTimer = null;
let audioChunks = [];
let recording = false;
let appReady = false;
let chapterCatalogLoaded = false;
const chapterCards = [];
const activeChapters = new Map();
let heatLoopStarted = false;
let currentAudioMode = null;
let currentObjectUrl = null;
let silentSink = null;
const RESULT_TTL_MS = 30000;
let lastPlaybackWindowIndex = -1;
let lastPlaybackPollAt = 0;

function setControlsEnabled(enabled) {
  typedInput.disabled = !enabled;
  micToggle.disabled = !enabled;
  micReset.disabled = !enabled;
  audioFileInput.disabled = !enabled;
  audioPlayer.disabled = !enabled;
}

async function pollStatus() {
  const response = await fetch("/api/status");
  const payload = await response.json();
  if (payload.status === "ready") {
    appReady = true;
    startupStatus.textContent = "Models loaded. Ready.";
    setControlsEnabled(true);
    if (!chapterCatalogLoaded) {
      await loadChapterCatalog();
    }
    startHeatLoop();
    return;
  }
  if (payload.status === "error") {
    startupStatus.textContent = `Startup failed: ${payload.error || "unknown error"}`;
    return;
  }
  startupStatus.textContent = "Loading local models. First startup can take a few minutes.";
  setControlsEnabled(false);
  setTimeout(() => {
    void pollStatus();
  }, 1500);
}

async function loadChapterCatalog() {
  const response = await fetch("/api/chapters");
  if (!response.ok) {
    wallMeta.textContent = "Chapter wall unavailable.";
    return;
  }
  const payload = await response.json();
  const fragment = document.createDocumentFragment();
  for (const chapter of payload.chapters) {
    const card = document.createElement("article");
    card.className = "chapter-card";
    card.innerHTML = `
      <div class="chapter-label">${chapter.short_label}</div>
      <div class="chapter-full">${chapter.id}</div>
      <div class="chapter-snippets"></div>
    `;
    card.title = chapter.id;
    fragment.appendChild(card);
    chapterCards[chapter.index] = card;
  }
  chapterWall.replaceChildren(fragment);
  chapterCatalogLoaded = true;
  wallMeta.textContent = `${payload.chapters.length.toLocaleString()} chapters visible at once`;
}

function heatColor(intensity) {
  const fill = 0.08 + intensity * 0.76;
  const edge = 0.10 + intensity * 0.62;
  const glow = 0.12 + intensity * 0.44;
  return {
    background: `linear-gradient(180deg, rgba(255,44,44,${fill * 0.42}), rgba(150,0,0,${fill}))`,
    boxShadow: `0 0 ${6 + intensity * 18}px rgba(255,44,44,${glow})`,
    borderColor: `rgba(255,72,72,${edge})`,
  };
}

function applyChapterState(index, state) {
  const card = chapterCards[index];
  if (!card) {
    return;
  }
  if (!state || state.intensity <= 0.02) {
    card.classList.remove("active");
    card.style.background = "";
    card.style.boxShadow = "";
    card.style.borderColor = "";
    card.style.color = "";
    activeChapters.delete(index);
    return;
  }
  card.classList.add("active");
  const color = heatColor(state.intensity);
  card.style.background = color.background;
  card.style.boxShadow = color.boxShadow;
  card.style.borderColor = color.borderColor;
  card.style.color = state.intensity > 0.45 ? "rgba(255,255,255,0.99)" : "rgba(255,255,255,0.92)";
}

function startHeatLoop() {
  if (heatLoopStarted) {
    return;
  }
  heatLoopStarted = true;
  const fadePerTick = 0.978;
  setInterval(() => {
    const now = Date.now();
    for (const [index, state] of activeChapters.entries()) {
      const ttlRatio = state.expiresAt ? Math.max(0, (state.expiresAt - now) / RESULT_TTL_MS) : 0;
      const nextIntensity = state.intensity * fadePerTick * Math.max(ttlRatio, 0.34);
      if (nextIntensity <= 0.02) {
        applyChapterState(index, null);
      } else {
        const nextState = { ...state, intensity: nextIntensity };
        activeChapters.set(index, nextState);
        applyChapterState(index, nextState);
      }
    }
  }, 120);
}

async function ensureSession() {
  if (!appReady) {
    throw new Error("App is still loading models.");
  }
  if (sessionId) {
    return sessionId;
  }
  const response = await fetch("/api/session");
  const payload = await response.json();
  sessionId = payload.session_id;
  return sessionId;
}

function renderState(payload) {
  const now = Date.now();
  const transcript = payload.transcript || "";
  transcriptText.textContent = transcript || "Waiting for input...";

  keywordChips.innerHTML = "";
  const keywords = (payload.keywords || "")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
  for (const keyword of keywords) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = keyword;
    keywordChips.appendChild(chip);
  }

  const items = payload.results || [];
  resultMeta.textContent = items.length
    ? `${new Set(items.map((item) => item.chapter_id)).size} chapters heated from the latest digest`
    : "No chapter heat yet.";
  if (payload.window_state) {
    const current = payload.window_state.current_seconds.toFixed(1);
    const target = payload.window_state.target_seconds.toFixed(0);
    const silence = payload.window_state.silence_seconds.toFixed(1);
    if (payload.mode === "file" && Number.isInteger(payload.window_state.window_index)) {
      const start = payload.window_state.window_start.toFixed(1);
      const end = payload.window_state.window_end.toFixed(1);
      windowStatus.textContent = `Chunk ${payload.window_state.window_index + 1}/${payload.window_state.window_count}: ${start}s-${end}s. Playback ${current}s.`;
    } else {
      windowStatus.textContent = `Digesting ${current}s / ${target}s. Silence ${silence}s. Trigger: ${payload.window_state.trigger}.`;
    }
  }

  const grouped = new Map();
  for (const item of items) {
    const existing = grouped.get(item.chapter_index) || {
      intensity: 0,
      chapterId: item.chapter_id,
    };
    existing.intensity = Math.max(existing.intensity, Math.max(item.highlight, 0.14));
    grouped.set(item.chapter_index, existing);
  }

  const seenIndexes = new Set(grouped.keys());
  for (const [chapterIndex, prior] of activeChapters.entries()) {
    if (!seenIndexes.has(chapterIndex)) {
      const cooled = {
        ...prior,
        intensity: prior.intensity * 0.58,
        expiresAt: now + 5000,
      };
      activeChapters.set(chapterIndex, cooled);
      applyChapterState(chapterIndex, cooled);
    }
  }

  for (const [chapterIndex, state] of grouped.entries()) {
    const prior = activeChapters.get(chapterIndex);
    const nextState = {
      intensity: Math.max(prior ? prior.intensity * 0.85 : 0, state.intensity),
      chapterId: state.chapterId,
      expiresAt: now + RESULT_TTL_MS,
    };
    activeChapters.set(chapterIndex, nextState);
    applyChapterState(chapterIndex, nextState);
  }
}

async function sendTypedQuery() {
  if (!appReady) {
    return;
  }
  const text = typedInput.value.trim();
  if (!text) {
    transcriptText.textContent = "Waiting for input...";
    keywordChips.innerHTML = "";
    resultMeta.textContent = "No chapter heat yet.";
    return;
  }

  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    if (response.status === 503) {
      startupStatus.textContent = "Still loading local models...";
    }
    return;
  }
  const payload = await response.json();
  renderState(payload);
}

typedInput.addEventListener("input", () => {
  clearTimeout(typedTimer);
  typedTimer = setTimeout(() => {
    void sendTypedQuery();
  }, 450);
});

function floatTo16BitPCM(float32Array) {
  const pcm = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, float32Array[i]));
    pcm[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return pcm;
}

function downsampleBuffer(buffer, inputSampleRate, outputSampleRate) {
  if (outputSampleRate === inputSampleRate) {
    return buffer;
  }
  const ratio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i += 1) {
      accum += buffer[i];
      count += 1;
    }
    result[offsetResult] = count ? accum / count : 0;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}

function encodeBase64FromInt16(int16Array) {
  let binary = "";
  const bytes = new Uint8Array(int16Array.buffer);
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    const subArray = bytes.subarray(i, i + chunk);
    binary += String.fromCharCode(...subArray);
  }
  return btoa(binary);
}

async function flushAudioChunk(statusLabel) {
  if (!appReady || !recording || !audioChunks.length || !audioContext) {
    return;
  }
  const targetSession = await ensureSession();
  const merged = new Float32Array(audioChunks.reduce((sum, part) => sum + part.length, 0));
  let offset = 0;
  for (const chunk of audioChunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  audioChunks = [];

  const downsampled = downsampleBuffer(merged, audioContext.sampleRate, 16000);
  const pcm16 = floatTo16BitPCM(downsampled);
  const payload = {
    session_id: targetSession,
    sample_rate: 16000,
    audio_base64: encodeBase64FromInt16(pcm16),
  };

  const response = await fetch("/api/audio-chunk", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    if (response.status === 503) {
      startupStatus.textContent = "Still loading local models...";
    }
    statusLabel.textContent = "Audio request failed.";
    return;
  }
  const data = await response.json();
  renderState(data);
  statusLabel.textContent = data.last_chunk_text ? `Live: ${data.last_chunk_text}` : "Listening...";
}

function ensureSilentSink() {
  if (!silentSink) {
    silentSink = audioContext.createGain();
    silentSink.gain.value = 0;
    silentSink.connect(audioContext.destination);
  }
}

function installAudioProcessor(streamOrElementSource) {
  ensureSilentSink();
  processor = audioContext.createScriptProcessor(4096, 1, 1);
  processor.onaudioprocess = (event) => {
    if (!recording) {
      return;
    }
    const data = event.inputBuffer.getChannelData(0);
    audioChunks.push(new Float32Array(data));
  };
  streamOrElementSource.connect(processor);
  processor.connect(silentSink);
}

function stopActiveAudioPipeline() {
  recording = false;
  clearInterval(flushTimer);
  flushTimer = null;
  audioChunks = [];
  if (processor) {
    processor.disconnect();
    processor = null;
  }
  if (source) {
    source.disconnect();
    source = null;
  }
  if (silentSink) {
    silentSink.disconnect();
    silentSink = null;
  }
  if (mediaStream) {
    for (const track of mediaStream.getTracks()) {
      track.stop();
    }
    mediaStream = null;
  }
  if (audioContext) {
    void audioContext.close();
    audioContext = null;
  }
  currentAudioMode = null;
}

async function resetSessionState() {
  const targetSession = await ensureSession();
  await fetch("/api/session/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: targetSession }),
  });
  renderState({ transcript: "", keywords: "", results: [] });
  for (const chapterIndex of [...activeChapters.keys()]) {
    applyChapterState(chapterIndex, null);
  }
  lastPlaybackWindowIndex = -1;
}

async function startMicrophone() {
  await ensureSession();
  if (currentAudioMode === "file") {
    audioPlayer.pause();
    stopActiveAudioPipeline();
  }
  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioContext = new AudioContext();
  source = audioContext.createMediaStreamSource(mediaStream);
  installAudioProcessor(source);
  recording = true;
  currentAudioMode = "mic";
  micToggle.textContent = "Stop Mic";
  micStatus.textContent = "Listening...";
  flushTimer = setInterval(() => {
    void flushAudioChunk(micStatus);
  }, 1000);
}

function stopMicrophone() {
  stopActiveAudioPipeline();
  micToggle.textContent = "Start Mic";
  micStatus.textContent = "Idle.";
}

async function startFilePlaybackProcessing() {
  await ensureSession();
  if (!audioPlayer.src) {
    fileStatus.textContent = "Load an audio file first.";
    return;
  }
  if (currentAudioMode === "mic") {
    stopMicrophone();
  }
  if (!audioContext) {
    audioContext = new AudioContext();
    source = audioContext.createMediaElementSource(audioPlayer);
    source.connect(audioContext.destination);
    installAudioProcessor(source);
  } else if (!processor) {
    installAudioProcessor(source);
  }
  await audioContext.resume();
  recording = true;
  currentAudioMode = "file";
  flushTimer = setInterval(() => {
    void flushAudioChunk(fileStatus);
  }, 1000);
}

function stopFilePlaybackProcessing() {
  if (currentAudioMode !== "file") {
    return;
  }
  recording = false;
  fileStatus.textContent = audioPlayer.src ? "Paused." : "No file loaded.";
  currentAudioMode = null;
}

micToggle.addEventListener("click", async () => {
  try {
    if (currentAudioMode === "mic") {
      stopMicrophone();
      return;
    }
    await startMicrophone();
  } catch (error) {
    micStatus.textContent = `Microphone unavailable: ${error.message}`;
    stopMicrophone();
  }
});

micReset.addEventListener("click", async () => {
  await resetSessionState();
  micStatus.textContent = currentAudioMode === "mic" ? "Listening..." : "Idle.";
  fileStatus.textContent = currentAudioMode === "file"
    ? "Playing..."
    : (audioPlayer.src ? "Paused." : "No file loaded.");
});

audioFileInput.addEventListener("change", async (event) => {
  const [file] = event.target.files || [];
  if (!file) {
    return;
  }
  if (currentAudioMode === "mic") {
    stopMicrophone();
  } else if (currentAudioMode === "file") {
    audioPlayer.pause();
    stopFilePlaybackProcessing();
  }
  if (currentObjectUrl) {
    URL.revokeObjectURL(currentObjectUrl);
  }
  currentObjectUrl = URL.createObjectURL(file);
  audioPlayer.src = currentObjectUrl;
  audioPlayer.load();
  await resetSessionState();
  const targetSession = await ensureSession();
  const formData = new FormData();
  formData.append("session_id", targetSession);
  formData.append("file", file);
  fileStatus.textContent = `Uploading and transcribing ${file.name}...`;
  const response = await fetch("/api/audio-file", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    fileStatus.textContent = "Audio file transcription failed.";
    return;
  }
  const payload = await response.json();
  lastPlaybackWindowIndex = -1;
  lastPlaybackPollAt = 0;
  fileStatus.textContent = `Ready: ${payload.window_count} chunks from ${payload.filename}`;
});

audioPlayer.addEventListener("play", async () => {
  try {
    currentAudioMode = "file";
    fileStatus.textContent = "Playing...";
  } catch (error) {
    fileStatus.textContent = `Audio file unavailable: ${error.message}`;
    stopFilePlaybackProcessing();
  }
});

audioPlayer.addEventListener("pause", () => {
  if (!audioPlayer.ended) {
    stopFilePlaybackProcessing();
  }
});

audioPlayer.addEventListener("ended", () => {
  stopFilePlaybackProcessing();
  fileStatus.textContent = "Playback finished.";
});

audioPlayer.addEventListener("seeking", async () => {
  if (audioPlayer.src) {
    lastPlaybackWindowIndex = -1;
    await requestPlaybackWindow(true);
    fileStatus.textContent = `Seeking to ${audioPlayer.currentTime.toFixed(1)}s`;
  }
});

async function requestPlaybackWindow(force = false) {
  if (!appReady || !audioPlayer.src) {
    return;
  }
  const now = performance.now();
  if (!force && now - lastPlaybackPollAt < 900) {
    return;
  }
  lastPlaybackPollAt = now;
  const targetSession = await ensureSession();
  const response = await fetch("/api/playback-window", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: targetSession,
      current_time: audioPlayer.currentTime,
    }),
  });
  if (!response.ok) {
    return;
  }
  const payload = await response.json();
  if (payload.window_state && Number.isInteger(payload.window_state.window_index)) {
    if (!force && payload.window_state.window_index === lastPlaybackWindowIndex) {
      return;
    }
    lastPlaybackWindowIndex = payload.window_state.window_index;
  }
  renderState(payload);
}

audioPlayer.addEventListener("timeupdate", () => {
  if (currentAudioMode === "file") {
    void requestPlaybackWindow(false);
  }
});

setControlsEnabled(false);
void pollStatus();
