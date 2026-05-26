/**
 * micro-interactions.ts
 * 3D tilt on cards, magnetic buttons, clip-path reveals
 * Loaded via Base.astro <script> for all pages
 */

// ═══════════════════════════════════════════
// 1. 3D TILT — cards with [data-tilt]
// ═══════════════════════════════════════════
function init3DTilt() {
 document.querySelectorAll<HTMLElement>('[data-tilt]').forEach(el => {
 if ((el as any).__tiltInit) return;
 (el as any).__tiltInit = true;

 const intensity = parseFloat(el.dataset.tilt || '6');
 const scale = parseFloat(el.dataset.tiltScale || '1.02');

 el.style.transformStyle = 'preserve-3d';
 el.style.willChange = 'transform';

 function onMove(e: MouseEvent) {
 const rect = el.getBoundingClientRect();
 const x = (e.clientX - rect.left) / rect.width - 0.5;
 const y = (e.clientY - rect.top) / rect.height - 0.5;

 el.style.transform =
 `perspective(600px) rotateY(${x * intensity}deg) rotateX(${-y * intensity}deg) scale3d(${scale},${scale},1)`;
 }

 function onLeave() {
 el.style.transform = '';
 el.style.transition = 'transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
 setTimeout(() => { el.style.transition = ''; }, 400);
 }

 el.addEventListener('mousemove', onMove);
 el.addEventListener('mouseleave', onLeave);
 });
}

// ═══════════════════════════════════════════
// 2. MAGNETIC BUTTONS — [data-magnetic]
// ═══════════════════════════════════════════
function initMagnetic() {
 document.querySelectorAll<HTMLElement>('[data-magnetic]').forEach(el => {
 if ((el as any).__magneticInit) return;
 (el as any).__magneticInit = true;

 const strength = parseFloat(el.dataset.magnetic || '0.25');
 let rafId = 0;
 let tx = 0, ty = 0, cx = 0, cy = 0;

 function onMove(e: MouseEvent) {
 const rect = el.getBoundingClientRect();
 const dx = e.clientX - (rect.left + rect.width / 2);
 const dy = e.clientY - (rect.top + rect.height / 2);
 tx = dx * strength;
 ty = dy * strength;
 if (!rafId) animate();
 }

 function animate() {
 cx += (tx - cx) * 0.15;
 cy += (ty - cy) * 0.15;
 el.style.transform = `translate3d(${cx}px,${cy}px,0)`;
 if (Math.abs(tx - cx) > 0.1 || Math.abs(ty - cy) > 0.1) {
 rafId = requestAnimationFrame(animate);
 } else {
 rafId = 0;
 }
 }

 function onLeave() {
 tx = 0; ty = 0;
 if (!rafId) animate();
 }

 el.addEventListener('mousemove', onMove);
 el.addEventListener('mouseleave', onLeave);
 });
}

// ═══════════════════════════════════════════
// 3. CLIP-PATH REVEAL — [data-reveal]
// ═══════════════════════════════════════════
function initClipReveal() {
 const reveals = document.querySelectorAll<HTMLElement>('[data-reveal]');
 if (!reveals.length) return;

 const obs = new IntersectionObserver((entries) => {
 entries.forEach(entry => {
 if (!entry.isIntersecting) return;
 const el = entry.target as HTMLElement;
 const dir = el.dataset.reveal || 'up';
 const delay = parseInt(el.dataset.revealDelay || '0');

 setTimeout(() => {
 switch (dir) {
 case 'up':
 el.style.clipPath = 'inset(0 0 0 0)';
 el.style.opacity = '1';
 el.style.transform = 'translateY(0)';
 break;
 case 'down':
 el.style.clipPath = 'inset(0 0 0 0)';
 el.style.opacity = '1';
 el.style.transform = 'translateY(0)';
 break;
 case 'left':
 el.style.clipPath = 'inset(0 0 0 0)';
 el.style.opacity = '1';
 el.style.transform = 'translateX(0)';
 break;
 case 'right':
 el.style.clipPath = 'inset(0 0 0 0)';
 el.style.opacity = '1';
 el.style.transform = 'translateX(0)';
 break;
 }
 el.classList.add('is-revealed');
 obs.unobserve(el);
 }, delay);
 });
 }, { threshold: 0.15 });

 reveals.forEach(el => {
 const dir = el.dataset.reveal || 'up';

 // Set initial hidden state
 switch (dir) {
 case 'up':
 el.style.clipPath = 'inset(100% 0 0 0)';
 el.style.transform = 'translateY(20px)';
 break;
 case 'down':
 el.style.clipPath = 'inset(0 0 100% 0)';
 el.style.transform = 'translateY(-20px)';
 break;
 case 'left':
 el.style.clipPath = 'inset(0 100% 0 0)';
 el.style.transform = 'translateX(20px)';
 break;
 case 'right':
 el.style.clipPath = 'inset(0 0 0 100%)';
 el.style.transform = 'translateX(-20px)';
 break;
 }

 el.style.opacity = '0';
 el.style.transition =
 'clip-path 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94), ' +
 'opacity 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94), ' +
 'transform 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94)';

 obs.observe(el);
 });
}

// ═══════════════════════════════════════════
// AUTO-ENHANCE: Apply data-tilt to post cards
// ═══════════════════════════════════════════
function autoEnhance() {
 document.querySelectorAll<HTMLElement>('.post-card:not([data-tilt])').forEach(el => {
 el.setAttribute('data-tilt', '4');
 el.setAttribute('data-tilt-scale', '1.01');
 });

 document.querySelectorAll<HTMLElement>('.nav-link:not([data-magnetic])').forEach(el => {
 el.setAttribute('data-magnetic', '0.2');
 });

 // Reveal on journal entries and sections
 document.querySelectorAll<HTMLElement>('.journal-entry:not([data-reveal])').forEach((el, i) => {
 el.setAttribute('data-reveal', 'up');
 el.setAttribute('data-reveal-delay', String(i * 80));
 });
}

// ═══════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════
function initAll() {
 autoEnhance();
 init3DTilt();
 initMagnetic();
 initClipReveal();
}

initAll();
document.addEventListener('astro:page-load', initAll);
document.addEventListener('astro:after-swap', initAll);
