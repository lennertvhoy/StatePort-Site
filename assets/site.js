(() => {
  document.documentElement.classList.add("js");

  const navToggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".site-nav");

  if (navToggle && nav) {
    navToggle.addEventListener("click", () => {
      const isOpen = nav.dataset.open === "true";
      nav.dataset.open = String(!isOpen);
      navToggle.setAttribute("aria-expanded", String(!isOpen));
    });

    nav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        nav.dataset.open = "false";
        navToggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const revealElements = document.querySelectorAll(".reveal");

  if (reducedMotion.matches || !("IntersectionObserver" in window)) {
    revealElements.forEach((element) => element.classList.add("is-visible"));
  } else {
    const observer = new IntersectionObserver(
      (entries, currentObserver) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            currentObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.13 },
    );

    revealElements.forEach((element) => observer.observe(element));
  }

  const hero = document.querySelector(".hero");
  const atlas = document.querySelector(".atlas");

  if (hero && atlas && !reducedMotion.matches && window.matchMedia("(pointer: fine)").matches) {
    hero.addEventListener("pointermove", (event) => {
      const bounds = hero.getBoundingClientRect();
      const x = (event.clientX - bounds.left) / bounds.width - 0.5;
      const y = (event.clientY - bounds.top) / bounds.height - 0.5;
      atlas.style.setProperty("--atlas-x", `${x * -18}px`);
      atlas.style.setProperty("--atlas-y", `${y * -14}px`);
    });

    hero.addEventListener("pointerleave", () => {
      atlas.style.setProperty("--atlas-x", "0px");
      atlas.style.setProperty("--atlas-y", "0px");
    });
  }

  const year = document.querySelector("[data-current-year]");
  if (year) {
    year.textContent = String(new Date().getFullYear());
  }
})();
