/* ==================== MOODMUSIC – APP.JS ==================== */

// ──────────────────────────────────────────────
// PLAYER
// ──────────────────────────────────────────────
const audioEl      = document.getElementById('audioEl');
const playerEl     = document.getElementById('player');
const playerTitle  = document.getElementById('playerTitle');
const playerArtist = document.getElementById('playerArtist');
const btnPlay      = document.getElementById('btnPlay');
const progressBar  = document.getElementById('progressBar');
const timeCurrent  = document.getElementById('timeCurrent');

let currentSong = null;

function playSong(titulo, artista) {
  showToast('Buscando preview…');

  fetch(`/preview/${encodeURIComponent(titulo)}/${encodeURIComponent(artista)}`)
    .then(r => r.json())
    .then(data => {
      if (data.preview_url) {
        currentSong = { titulo, artista };
        playerTitle.textContent  = titulo;
        playerArtist.textContent = artista;
        audioEl.src = data.preview_url;
        audioEl.play();
        btnPlay.textContent = '⏸';
        playerEl.classList.remove('hidden');
        showToast('▶ Reproduciendo preview de 30s');
      } else {
        showToast('Preview no disponible para esta canción');
      }
    })
    .catch(() => showToast('Error al obtener preview'));
}

function togglePlay() {
  if (!audioEl.src) return;
  if (audioEl.paused) { audioEl.play(); btnPlay.textContent = '⏸'; }
  else                 { audioEl.pause(); btnPlay.textContent = '▶'; }
}

function seekAudio(val) {
  audioEl.currentTime = val;
}

function closePlayer() {
  audioEl.pause();
  audioEl.src = '';
  playerEl.classList.add('hidden');
  btnPlay.textContent = '▶';
}

audioEl.addEventListener('timeupdate', () => {
  const t = audioEl.currentTime;
  progressBar.value     = t;
  timeCurrent.textContent = fmt(t);
});
audioEl.addEventListener('ended', () => {
  btnPlay.textContent = '▶';
  progressBar.value   = 0;
  timeCurrent.textContent = '0:00';
});

function fmt(s) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

// ──────────────────────────────────────────────
// RECOMENDACIONES
// ──────────────────────────────────────────────
const formRec      = document.getElementById('formRecomendar');
const secRec       = document.getElementById('secRecomendaciones');
const gridRec      = document.getElementById('gridRecomendadas');
const btnRecText   = document.getElementById('btnText');
const btnRecBtn    = document.getElementById('btnRecomendar');

if (formRec) {
  formRec.addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(formRec);

    btnRecBtn.disabled = true;
    btnRecText.innerHTML = '<span class="spinner"></span> Buscando…';

    try {
      const res  = await fetch('/recomendar', { method: 'POST', body: fd });
      const data = await res.json();

      if (data.error) {
        showToast('⚠ ' + data.error);
        return;
      }

      const canciones = data.recomendaciones || [];
      if (canciones.length === 0) {
        gridRec.innerHTML = '<p style="color:var(--muted);padding:16px">No se encontraron canciones para esta combinación.</p>';
      } else {
        gridRec.innerHTML = canciones.map(songCardHTML).join('');
      }

      secRec.classList.remove('hidden');
      secRec.scrollIntoView({ behavior: 'smooth', block: 'start' });
      showToast(`🎵 ${canciones.length} canciones recomendadas`);
    } catch (err) {
      showToast('Error al obtener recomendaciones');
    } finally {
      btnRecBtn.disabled = false;
      btnRecText.textContent = '🎵 Recomendar';
    }
  });
}

// ──────────────────────────────────────────────
// LIKE / DISLIKE
// ──────────────────────────────────────────────
function reaccion(cancionId, tipo, btn) {
  const endpoint = tipo === 'like' ? '/me_gusta' : '/no_me_gusta';
  const fd = new FormData();
  fd.append('cancion_id', cancionId);

  fetch(endpoint, { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (tipo === 'like') {
        btn.classList.add('active-like');
        // Quitar active-dislike del hermano si existe
        const card = btn.closest('.song-card');
        card.querySelector('.btn-dislike')?.classList.remove('active-dislike');
        showToast('♥ Agregado a favoritos');
      } else {
        btn.classList.add('active-dislike');
        const card = btn.closest('.song-card');
        card.querySelector('.btn-like')?.classList.remove('active-like');
        // Ocultar la tarjeta de recomendaciones si está en esa sección
        const inRec = card.closest('#gridRecomendadas');
        if (inRec) {
          card.style.opacity = '0';
          card.style.transform = 'scale(0.95)';
          setTimeout(() => card.remove(), 300);
        }
        showToast('✕ Canción excluida de recomendaciones');
      }
    })
    .catch(() => showToast('Error al registrar reacción'));
}

// ──────────────────────────────────────────────
// EXPLORAR POR GÉNERO
// ──────────────────────────────────────────────
const genreTabs  = document.getElementById('genreTabs');
const gridGenero = document.getElementById('gridGenero');

if (genreTabs) {
  genreTabs.addEventListener('click', e => {
    const btn = e.target.closest('.genre-tab');
    if (!btn) return;

    const genre = btn.dataset.genre;

    // Estado activo
    genreTabs.querySelectorAll('.genre-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    gridGenero.innerHTML = '<p style="color:var(--muted);padding:16px">Cargando…</p>';

    fetch(`/explorar/${encodeURIComponent(genre)}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          gridGenero.innerHTML = `<p style="color:var(--muted);padding:16px">${data.error}</p>`;
          return;
        }
        const canciones = data.canciones || [];
        gridGenero.innerHTML = canciones.length
          ? canciones.map(songCardSimpleHTML).join('')
          : '<p style="color:var(--muted);padding:16px">Sin canciones en este género.</p>';
        gridGenero.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      })
      .catch(() => {
        gridGenero.innerHTML = '<p style="color:var(--muted);padding:16px">Error al cargar canciones.</p>';
      });
  });
}

// ──────────────────────────────────────────────
// HTML helpers
// ──────────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function songCardHTML(c) {
  return `
<div class="song-card" data-id="${esc(c.id)}">
  <div class="song-meta">
    <div class="song-cover">🎵</div>
    <div>
      <div class="song-title">${esc(c.titulo)}</div>
      <div class="song-artist">${esc(c.artista)}</div>
      <div class="song-tags">
        <span class="tag tag-genre">${esc(c.genero)}</span>
        <span class="tag tag-mood">${esc(c.animo)}</span>
        <span class="tag tag-ctx">${esc(c.contexto)}</span>
      </div>
    </div>
  </div>
  <div class="song-actions">
    <span class="song-rating">★ ${Number(c.calificacion).toFixed(1)}</span>
    <span class="song-duration">${esc(c.duracion)}</span>
    <button class="btn-icon btn-play-song" title="Reproducir"
      onclick="playSong('${esc(c.titulo)}','${esc(c.artista)}')">▶</button>
    <button class="btn-icon btn-like" title="Me gusta"
      onclick="reaccion('${esc(c.id)}','like',this)">♥</button>
    <button class="btn-icon btn-dislike" title="No me gusta"
      onclick="reaccion('${esc(c.id)}','dislike',this)">✕</button>
  </div>
</div>`;
}

function songCardSimpleHTML(c) {
  return `
<div class="song-card" data-id="${esc(c.id)}">
  <div class="song-meta">
    <div class="song-cover">🎵</div>
    <div>
      <div class="song-title">${esc(c.titulo)}</div>
      <div class="song-artist">${esc(c.artista)}</div>
      <div class="song-tags">
        <span class="tag tag-genre">${esc(c.genero)}</span>
      </div>
    </div>
  </div>
  <div class="song-actions">
    <span class="song-rating">★ ${Number(c.calificacion).toFixed(1)}</span>
    <span class="song-duration">${esc(c.duracion)}</span>
    <button class="btn-icon btn-play-song" title="Reproducir"
      onclick="playSong('${esc(c.titulo)}','${esc(c.artista)}')">▶</button>
    <button class="btn-icon btn-like" title="Me gusta"
      onclick="reaccion('${esc(c.id)}','like',this)">♥</button>
    <button class="btn-icon btn-dislike" title="No me gusta"
      onclick="reaccion('${esc(c.id)}','dislike',this)">✕</button>
  </div>
</div>`;
}

// ──────────────────────────────────────────────
// TOAST
// ──────────────────────────────────────────────
let _toastTimer = null;

function showToast(msg) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.remove('hidden');

  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => toast.classList.add('hidden'), 2800);
}
