class ParticleSystem {
    constructor() {
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'particles-canvas';
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.animationId = null;
        this.maxParticles = 30;
        this.particleColor = '160, 120, 100';

        document.body.prepend(this.canvas);
        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.init();
        this.animate();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    init() {
        for (let i = 0; i < this.maxParticles; i++) {
            this.particles.push(this.createParticle());
        }
    }

    createParticle() {
        return {
            x: Math.random() * this.canvas.width,
            y: Math.random() * this.canvas.height,
            size: Math.random() * 1.2 + 0.3,
            speedX: (Math.random() - 0.5) * 0.15,
            speedY: (Math.random() - 0.5) * 0.15,
            opacity: Math.random() * 0.15 + 0.03,
            pulse: Math.random() * Math.PI * 2,
            pulseSpeed: Math.random() * 0.02 + 0.005,
        };
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        this.particles.forEach(p => {
            p.x += p.speedX;
            p.y += p.speedY;
            p.pulse += p.pulseSpeed;

            if (p.x < 0) p.x = this.canvas.width;
            if (p.x > this.canvas.width) p.x = 0;
            if (p.y < 0) p.y = this.canvas.height;
            if (p.y > this.canvas.height) p.y = 0;

            const currentOpacity = p.opacity * (0.6 + 0.4 * Math.sin(p.pulse));

            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(${this.particleColor}, ${currentOpacity})`;
            this.ctx.fill();

            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size * 3, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(${this.particleColor}, ${currentOpacity * 0.15})`;
            this.ctx.fill();
        });

        for (let i = 0; i < this.particles.length; i++) {
            for (let j = i + 1; j < this.particles.length; j++) {
                const dx = this.particles[i].x - this.particles[j].x;
                const dy = this.particles[i].y - this.particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 100) {
                    const lineOpacity = (1 - dist / 100) * 0.03;
                    this.ctx.beginPath();
                    this.ctx.moveTo(this.particles[i].x, this.particles[i].y);
                    this.ctx.lineTo(this.particles[j].x, this.particles[j].y);
                    this.ctx.strokeStyle = `rgba(${this.particleColor}, ${lineOpacity})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            }
        }

        this.animationId = requestAnimationFrame(() => this.animate());
    }
}
if (!window.matchMedia || !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    window.particles = new ParticleSystem();
}

const slides  = Array.from(document.querySelectorAll('.slide'));
const total   = slides.length;
let current   = 0;
let animating = false;
let hintTimer = null;

const fill    = document.getElementById('progressFill');
const counter = document.getElementById('counter');
const ASSETS = (document.querySelector('script[src*="nexus.js"]') || {src:''}).src.replace(/nexus\.js.*$/, '');

function updateUI() {
    if (fill)    fill.style.width    = ((current + 1) / total * 100) + '%';
    if (counter) counter.textContent = (current + 1) + ' / ' + total;
    const prev = document.getElementById('prevBtn');
    const next = document.getElementById('nextBtn');
    if (prev) prev.disabled = current === 0;
    if (next) next.disabled = current === total - 1;
    if (slides[current].id) history.replaceState(null, null, '#' + slides[current].id);
    const hint = document.querySelector('.kb-hint');
    if (hint) {
        if (current === 0) {
            hint.classList.remove('hidden');
            clearTimeout(hintTimer);
            hintTimer = setTimeout(() => { hint.classList.add('hidden'); }, 4000);
        } else {
            hint.classList.add('hidden');
        }
    }
}
function animateCounter(element, start, end, duration) {
    let startTime = null;
    const isDecimal = end % 1 !== 0;

    const step = (currentTime) => {
        if (!startTime) startTime = currentTime;
        const progress = Math.min((currentTime - startTime) / duration, 1);
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const value = start + (end - start) * easeOutQuart;
        element.textContent = isDecimal ? value.toFixed(1) : Math.floor(value).toLocaleString();

        if (progress < 1) {
            requestAnimationFrame(step);
        } else {
            element.textContent = isDecimal ? end.toFixed(1) : end.toLocaleString();
            const card = element.closest('.stat-card');
            if (card) {
                card.style.boxShadow = '0 0 30px rgba(245, 107, 53, 0.25)';
                setTimeout(() => { card.style.boxShadow = ''; }, 600);
            }
        }
    };

    requestAnimationFrame(step);
}

function animateStatCounters(slideEl) {
    const stats = slideEl.querySelectorAll('.stat-number[data-target]');
    stats.forEach((stat, i) => {
        const raw = stat.getAttribute('data-target');
        if (!/^-?[\d.]+$/.test(raw)) return;  // skip non-numeric targets (e.g. "~50", "672h") — parseFloat would render "672" for "672h"
        const target = parseFloat(raw);
        if (!Number.isFinite(target)) return;  // e.g. "." passes the shape test but parses to NaN
        stat.textContent = '0';
        setTimeout(() => { animateCounter(stat, 0, target, 2000); }, 800 + i * 200);
    });
}

function goTo(idx, dir) {
    if (animating || idx === current || idx < 0 || idx >= total) return;
    animating = true;
    const from = slides[current];
    const to   = slides[idx];
    from.classList.add(dir === 1 ? 'exit-fwd' : 'exit-bwd');
    setTimeout(() => {
        from.classList.remove('active','exit-fwd','exit-bwd');
        from.style.display = 'none';
        to.style.display   = 'flex';
        void to.offsetHeight;
        to.classList.add('active');
        animateStatCounters(to);
        current = idx;
        updateUI();
        setTimeout(() => { animating = false; }, 560);
    }, 360);
}

const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
if (prevBtn) prevBtn.addEventListener('click', () => goTo(current - 1, -1));
if (nextBtn) nextBtn.addEventListener('click', () => goTo(current + 1,  1));
let gridOpen = false;
const SLIDE_META = window.SLIDE_META || {};

function buildGrid() {
    const container = document.getElementById('gridThumbnails');
    if (!container) return;
    container.innerHTML = '';
    slides.forEach((slide, i) => {
        const thumb = document.createElement('div');
        thumb.className = 'grid-thumb' + (i === current ? ' current' : '');
        const meta = SLIDE_META[slide.id] || {};
        const labelEl = slide.querySelector('.sec-eyebrow');
        const titleEl = slide.querySelector('.slide-title') || slide.querySelector('.hero-title .line-break');
        const label = meta.label || (labelEl ? labelEl.textContent.trim() : '');
        const title = meta.title || (titleEl ? titleEl.textContent.trim().replace(/\s+/g, ' ') : 'Slide ' + (i + 1));
        thumb.innerHTML = '<div class="grid-thumb-num">' + (i + 1) + '</div>'
            + (label ? '<div class="grid-thumb-label">' + label + '</div>' : '')
            + '<div class="grid-thumb-title">' + title + '</div>';
        thumb.onclick = () => { const target = i; closeGrid(); goTo(target, target > current ? 1 : -1); };
        container.appendChild(thumb);
    });
}

function openGrid()   { const o = document.getElementById('gridOverlay'); if (!o) return; buildGrid(); o.classList.add('open'); gridOpen = true; }
function closeGrid()  { const o = document.getElementById('gridOverlay'); if (o) o.classList.remove('open'); gridOpen = false; }
function toggleGrid() { gridOpen ? closeGrid() : openGrid(); }
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
    } else {
        document.exitFullscreen();
    }
}
let lightboxOpen = false;
function openLightbox(src) {
    const img = document.getElementById('lightboxImg');
    const overlay = document.getElementById('lightboxOverlay');
    if (!img || !overlay) return;
    img.src = src;
    overlay.classList.add('open');
    lightboxOpen = true;
}
function closeLightbox() {
    const overlay = document.getElementById('lightboxOverlay');
    if (overlay) overlay.classList.remove('open');
    lightboxOpen = false;
}
let legendEl = null, legendOpen = false;

function buildLegend() {
    if (legendEl) return legendEl;
    legendEl = document.createElement('div');
    legendEl.className = 'legend-overlay';
    legendEl.innerHTML = `
        <div class="legend-card">
            <div class="legend-title">Keyboard Shortcuts</div>
            <div class="legend-row"><div class="legend-keys"><kbd>→</kbd><kbd>↓</kbd><kbd>Space</kbd></div><div class="legend-action">Next slide</div></div>
            <div class="legend-row"><div class="legend-keys"><kbd>←</kbd><kbd>↑</kbd></div><div class="legend-action">Previous slide</div></div>
            <div class="legend-row"><div class="legend-keys"><kbd>Home</kbd></div><div class="legend-action">First slide</div></div>
            <div class="legend-row"><div class="legend-keys"><kbd>End</kbd></div><div class="legend-action">Last slide</div></div>
            <div class="legend-row"><div class="legend-keys"><kbd>G</kbd></div><div class="legend-action">Slide grid</div></div>
            <div class="legend-row"><div class="legend-keys"><kbd>C</kbd></div><div class="legend-action">Confetti</div></div>
            <div class="legend-row"><div class="legend-keys"><kbd>P</kbd></div><div class="legend-action">Presenter view (Ctrl/Cmd+P prints)</div></div>
            <div class="legend-row"><div class="legend-keys"><kbd>F</kbd></div><div class="legend-action">Fullscreen</div></div>
            <div class="legend-row"><div class="legend-keys"><kbd>L</kbd></div><div class="legend-action">This legend</div></div>
            <div class="legend-row"><div class="legend-keys"><kbd>Esc</kbd></div><div class="legend-action">Close overlay</div></div>
            <div class="legend-dismiss">Press L or Esc to close</div>
        </div>`;
    legendEl.addEventListener('click', (e) => { if (e.target === legendEl) closeLegend(); });
    document.body.appendChild(legendEl);
    return legendEl;
}
let legendHideTimer = null;
function openLegend()   { const el = buildLegend(); clearTimeout(legendHideTimer); legendHideTimer = null; el.style.display = 'flex'; void el.offsetWidth; el.classList.add('open'); legendOpen = true; }
function closeLegend()  { if (!legendEl) return; legendEl.classList.remove('open'); legendOpen = false; clearTimeout(legendHideTimer); legendHideTimer = setTimeout(() => { if (legendEl) legendEl.style.display = 'none'; }, 250); }
function toggleLegend() { legendOpen ? closeLegend() : openLegend(); }
let peekEl = null, peekOpen = false;

function buildPeek() {
    if (peekEl) return peekEl;
    peekEl = document.createElement('div');
    peekEl.className = 'slide-peek-overlay';
    peekEl.innerHTML = '<div class="slide-peek-frame">'
        + '<button class="slide-peek-close" aria-label="Close preview"><i class="fa-solid fa-xmark"></i></button>'
        + '<div class="slide-peek-viewport"></div></div>';
    peekEl.addEventListener('click', (e) => { if (e.target === peekEl) closeSlidePeek(); });
    peekEl.querySelector('.slide-peek-close').addEventListener('click', closeSlidePeek);
    document.body.appendChild(peekEl);
    return peekEl;
}

function openSlidePeek(sourceId) {
    const src = document.getElementById(sourceId);
    if (!src) return;
    const overlay  = buildPeek();
    const frame    = overlay.querySelector('.slide-peek-frame');
    const viewport = overlay.querySelector('.slide-peek-viewport');
    const k = 0.9;
    frame.style.width  = Math.round(window.innerWidth  * k) + 'px';
    frame.style.height = Math.round(window.innerHeight * k) + 'px';
    viewport.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:absolute;top:0;left:0;width:100vw;height:100vh;transform-origin:top left;transform:scale(' + k + ');';
    const clone = src.cloneNode(true);
    clone.removeAttribute('id');
    clone.classList.add('active');
    clone.style.display = 'flex';
    wrap.appendChild(clone);
    viewport.appendChild(wrap);
    overlay.classList.add('open');
    peekOpen = true;
}

function closeSlidePeek() {
    if (!peekEl) return;
    peekEl.classList.remove('open');
    peekEl.querySelector('.slide-peek-viewport').innerHTML = '';
    peekOpen = false;
}

window.openSlidePeek = openSlidePeek;
let confettiCooldown = false;

function launchConfetti() {
    if (confettiCooldown) return;
    confettiCooldown = true;
    setTimeout(() => { confettiCooldown = false; }, 3500);

    const canvas = document.createElement('canvas');
    canvas.className = 'confetti-canvas';
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');

    const logo = document.createElement('img');
    logo.src = ASSETS + 'clouds-on-mars-signet.png';
    logo.className = 'confetti-logo';
    document.body.appendChild(logo);
    requestAnimationFrame(() => { logo.classList.add('show'); });
    setTimeout(() => { logo.classList.replace('show', 'fade'); }, 1800);
    setTimeout(() => { logo.remove(); }, 2400);

    const colors = ['#F56B35', '#E8652F', '#FFB899', '#FFC857', '#FFFFFF', '#D5582E'];
    const particles = [];
    for (let i = 0; i < 120; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = Math.random() * 8 + 3;
        particles.push({
            x: canvas.width / 2, y: canvas.height / 2,
            vx: Math.cos(angle) * speed * (0.5 + Math.random()),
            vy: Math.sin(angle) * speed * (0.5 + Math.random()) - 3,
            size: Math.random() * 6 + 3,
            color: colors[Math.floor(Math.random() * colors.length)],
            rotation: Math.random() * 360,
            rotSpeed: (Math.random() - 0.5) * 12,
            opacity: 1,
            shape: Math.random() > 0.5 ? 'rect' : 'circle',
        });
    }
    const durationMs = 3000;
    let startTime = null;

    function animate(now) {
        if (startTime === null) startTime = now;
        const progress = Math.min(1, (now - startTime) / durationMs);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => {
            p.x += p.vx; p.vy += 0.12; p.y += p.vy; p.vx *= 0.99;
            p.rotation += p.rotSpeed;
            p.opacity = 1 - progress;
            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate((p.rotation * Math.PI) / 180);
            ctx.globalAlpha = p.opacity;
            ctx.fillStyle = p.color;
            if (p.shape === 'rect') {
                ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
            } else {
                ctx.beginPath();
                ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.restore();
        });
        if (progress < 1) { requestAnimationFrame(animate); } else { canvas.remove(); }
    }
    requestAnimationFrame(animate);
}
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        if (lightboxOpen) { closeLightbox();  return; }
        if (peekOpen)     { closeSlidePeek(); return; }
        if (gridOpen)     { closeGrid();      return; }
        if (legendOpen)   { closeLegend();    return; }
        return;
    }
    if (lightboxOpen || peekOpen) return;
    if (e.ctrlKey || e.metaKey) return;
    const k = e.key.toLowerCase();
    if (k === 'g') { e.preventDefault(); toggleGrid();       return; }
    if (k === 'f') { e.preventDefault(); toggleFullscreen(); return; }
    if (k === 'l') { toggleLegend();   return; }
    if (k === 'c') { launchConfetti(); return; }
    if (gridOpen || legendOpen) return;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ' || e.key === 'PageDown') { e.preventDefault(); goTo(current + 1,  1); }
    if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp'   || e.key === 'PageUp')                    { e.preventDefault(); goTo(current - 1, -1); }
    if (e.key === 'Home') { e.preventDefault(); goTo(0, -1); }
    if (e.key === 'End')  { e.preventDefault(); goTo(total - 1, 1); }
});

let tx = null;
document.addEventListener('touchstart', e => { tx = e.touches[0].clientX; });
document.addEventListener('touchend',   e => {
    if (tx === null) return;
    const dx = e.changedTouches[0].clientX - tx;
    if (Math.abs(dx) > 40) goTo(current + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1);
    tx = null;
});
(function () {
    const id = location.hash.slice(1);
    const idx = slides.findIndex(s => s.id === id);
    if (idx > 0) {
        slides[current].classList.remove('active');
        slides[current].style.display = 'none';
        slides[idx].style.display = 'flex';
        slides[idx].classList.add('active');
        current = idx;
    }
})();

animateStatCounters(slides[current]);
updateUI();
(function () {
    const notice = document.getElementById('mobileNotice');
    if (!notice || window.innerWidth > 768) return;
    setTimeout(() => { notice.style.opacity = '0'; }, 5000);
    setTimeout(() => { notice.style.display = 'none'; }, 5800);
})();

const spotlight = document.getElementById('spotlight');
if (spotlight) {
    document.addEventListener('mousemove', e => {
        spotlight.style.left    = e.clientX + 'px';
        spotlight.style.top     = e.clientY + 'px';
        spotlight.style.opacity = '1';
    });
    document.addEventListener('mouseleave', () => { spotlight.style.opacity = '0'; });
}
document.addEventListener('visibilitychange', () => {
    if (!window.particles) return;
    if (document.visibilityState === 'hidden') {
        cancelAnimationFrame(window.particles.animationId);
    } else {
        window.particles.animate();
    }
});
let particlesResizeTimeout;
window.addEventListener('resize', () => {
    if (!window.particles) return;
    clearTimeout(particlesResizeTimeout);
    particlesResizeTimeout = setTimeout(() => { window.particles.resize(); }, 250);
});
