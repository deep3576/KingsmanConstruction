// Hero slider
const slides = Array.from(document.querySelectorAll('.hero-slide'));
let idx = 0;
setInterval(() => {
  if (!slides.length) return;
  slides[idx].classList.remove('is-active');
  idx = (idx + 1) % slides.length;
  slides[idx].classList.add('is-active');
}, 5200);

// Reveal on scroll
const io = new IntersectionObserver(entries=>{
  entries.forEach(e=>{
    if(e.isIntersecting){ e.target.classList.add('visible'); io.unobserve(e.target); }
  });
},{threshold:0.15});
document.querySelectorAll('.reveal').forEach(el=>io.observe(el));

// Before/After slider
const ba = document.querySelector('.ba-wrap');
if (ba){
  const range = ba.querySelector('.ba-range');
  const afterImg = ba.querySelector('.ba-after img');
  const setClip = v => { afterImg.style.clipPath = `inset(0 0 0 ${v}%)`; };
  setClip(50);
  range.addEventListener('input', e => setClip(e.target.value));
}

// Lightbox
const lb = document.getElementById('lightbox');
if (lb){
  const lbImg = lb.querySelector('.lightbox-img');
  const close = () => { lb.classList.remove('open'); lb.setAttribute('aria-hidden','true'); lbImg.src=''; lbImg.alt=''; };
  document.querySelectorAll('.gallery-item').forEach(a=>{
    a.addEventListener('click', e=>{
      e.preventDefault();
      lbImg.src = a.href; lbImg.alt = a.querySelector('img').alt;
      lb.classList.add('open'); lb.setAttribute('aria-hidden','false');
    });
  });
  lb.addEventListener('click', (e)=>{ if(e.target===lb) close(); });
  lb.querySelector('.lightbox-close').addEventListener('click', close);
  document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') close(); });
}
