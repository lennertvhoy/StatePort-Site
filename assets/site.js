(() => {
  "use strict";

  const root = document.documentElement;
  root.classList.add("js");

  const currentScript = document.currentScript;
  const siteRoot = currentScript
    ? new URL("../", currentScript.src)
    : new URL("./", window.location.href);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const routeLabels = {
    "docs/": "Documentation",
    "docs/foundations.html": "Why StatePort exists",
    "docs/model.html": "Core model",
    "docs/lifecycle.html": "Lifecycle",
    "docs/governance.html": "Governed change",
    "docs/security-and-privacy.html": "Security and privacy",
    "docs/hosts-and-portability.html": "Hosts and portability",
    "docs/platform-support.html": "Platform support",
    "docs/evidence-and-roadmap.html": "Evidence and roadmap",
    "docs/reference.html": "Reference and FAQ",
    "docs/prototype-walkthrough.html": "Prototype walkthrough",
    "docs/agent-kits.html": "Agent Kits roadmap",
    "docs/getting-started.html": "StateSpec basics",
    "tutorials/": "Tutorials",
    "tutorials/first-application.html": "First application",
    "tutorials/reading-a-receipt.html": "Read a receipt",
    "papers/stateware-whitepaper-public-v1.1.html": "Stateware paper",
    "releases/": "Release status",
    "404.html": "Page not found",
  };

  const documentationSequence = [
    ["docs/", "Documentation home"],
    ["docs/foundations.html", "Why StatePort exists"],
    ["docs/model.html", "Core model"],
    ["docs/lifecycle.html", "Lifecycle"],
    ["docs/governance.html", "Governed change"],
    ["docs/security-and-privacy.html", "Security and privacy"],
    ["docs/hosts-and-portability.html", "Hosts and portability"],
    ["docs/platform-support.html", "Platform support"],
    ["docs/evidence-and-roadmap.html", "Evidence and roadmap"],
    ["docs/reference.html", "Reference and FAQ"],
    ["docs/prototype-walkthrough.html", "Prototype walkthrough"],
    ["docs/getting-started.html", "StateSpec basics"],
    ["docs/agent-kits.html", "Agent Kits roadmap"],
  ];

  const tutorialSequence = [
    ["tutorials/", "Tutorials home"],
    ["tutorials/first-application.html", "Design a first application"],
    ["tutorials/reading-a-receipt.html", "Read a governed receipt"],
  ];

  function relativePath(url = window.location.href) {
    const pathname = new URL(url, window.location.href).pathname;
    const rootPath = siteRoot.pathname;
    if (!pathname.startsWith(rootPath)) {
      return pathname.replace(/^\/+/, "");
    }
    return decodeURIComponent(pathname.slice(rootPath.length)).replace(/^\/+/, "");
  }

  function ensureEnhancementStyles() {
    if (document.querySelector("link[data-site-enhancements]")) {
      return;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = new URL("assets/site-enhancements.css", siteRoot).href;
    link.dataset.siteEnhancements = "";
    document.head.append(link);
  }

  function setNavigationFocusability(nav, links, focusable) {
    if ("inert" in nav) {
      nav.inert = !focusable;
    }
    links.forEach((link) => {
      if (focusable) {
        link.removeAttribute("tabindex");
      } else {
        link.tabIndex = -1;
      }
    });
  }

  function initPrimaryNavigation() {
    const navToggle = document.querySelector(".nav-toggle");
    const nav = document.querySelector(".site-nav");
    if (!navToggle || !nav) {
      return;
    }

    const mobileViewport = window.matchMedia("(max-width: 800px)");
    const links = [...nav.querySelectorAll("a")];
    const label = navToggle.querySelector(".sr-only");

    const setMenu = (open, { focusFirst = false, restoreFocus = false } = {}) => {
      nav.dataset.open = String(open);
      navToggle.setAttribute("aria-expanded", String(open));
      if (label) {
        label.textContent = open ? "Close navigation" : "Open navigation";
      }

      if (mobileViewport.matches) {
        nav.setAttribute("aria-hidden", String(!open));
        setNavigationFocusability(nav, links, open);
      } else {
        nav.removeAttribute("aria-hidden");
        setNavigationFocusability(nav, links, true);
      }

      if (focusFirst && links[0]) {
        links[0].focus();
      }
      if (restoreFocus) {
        navToggle.focus();
      }
    };

    const syncViewport = () => setMenu(false);
    syncViewport();

    navToggle.addEventListener("click", () => {
      const open = nav.dataset.open !== "true";
      setMenu(open, { focusFirst: open });
    });

    links.forEach((link) => {
      link.addEventListener("click", () => {
        if (mobileViewport.matches) {
          setMenu(false);
        }
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && nav.dataset.open === "true" && mobileViewport.matches) {
        setMenu(false, { restoreFocus: true });
      }
    });

    document.addEventListener("pointerdown", (event) => {
      if (
        mobileViewport.matches &&
        nav.dataset.open === "true" &&
        !nav.contains(event.target) &&
        !navToggle.contains(event.target)
      ) {
        setMenu(false);
      }
    });

    if (typeof mobileViewport.addEventListener === "function") {
      mobileViewport.addEventListener("change", syncViewport);
    } else {
      mobileViewport.addListener(syncViewport);
    }
  }

  function initReveals() {
    const elements = [...document.querySelectorAll(".reveal")];
    const revealAll = () => elements.forEach((element) => element.classList.add("is-visible"));

    if (reducedMotion.matches || !("IntersectionObserver" in window)) {
      revealAll();
      return;
    }

    const observer = new IntersectionObserver(
      (entries, currentObserver) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            currentObserver.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -6%", threshold: 0.08 },
    );

    elements.forEach((element) => observer.observe(element));
  }

  function initAtlasParallax() {
    const hero = document.querySelector(".hero");
    const atlas = document.querySelector(".atlas");
    if (!hero || !atlas || reducedMotion.matches || !window.matchMedia("(pointer: fine)").matches) {
      return;
    }

    let pendingFrame = 0;
    let nextX = 0;
    let nextY = 0;

    const render = () => {
      atlas.style.setProperty("--atlas-x", `${nextX * -18}px`);
      atlas.style.setProperty("--atlas-y", `${nextY * -14}px`);
      pendingFrame = 0;
    };

    hero.addEventListener("pointermove", (event) => {
      const bounds = hero.getBoundingClientRect();
      nextX = (event.clientX - bounds.left) / bounds.width - 0.5;
      nextY = (event.clientY - bounds.top) / bounds.height - 0.5;
      if (!pendingFrame) {
        pendingFrame = window.requestAnimationFrame(render);
      }
    });

    hero.addEventListener("pointerleave", () => {
      nextX = 0;
      nextY = 0;
      if (!pendingFrame) {
        pendingFrame = window.requestAnimationFrame(render);
      }
    });
  }

  function initPrototypeGallery() {
    const gallery = document.getElementById("prototype-gallery");
    const items = [...document.querySelectorAll("[data-prototype-gallery-item]")];
    if (!gallery || !items.length || typeof gallery.showModal !== "function") {
      return;
    }

    const image = gallery.querySelector("[data-prototype-gallery-image]");
    const counter = gallery.querySelector("[data-prototype-gallery-counter]");
    const label = gallery.querySelector("[data-prototype-gallery-label]");
    const summary = gallery.querySelector("[data-prototype-gallery-summary]");
    const status = gallery.querySelector("[data-prototype-gallery-status]");
    const closeButton = gallery.querySelector("[data-prototype-gallery-close]");
    const previousButton = gallery.querySelector("[data-prototype-gallery-previous]");
    const nextButton = gallery.querySelector("[data-prototype-gallery-next]");
    if (!image || !counter || !label || !summary || !status || !closeButton || !previousButton || !nextButton) {
      return;
    }

    let currentIndex = 0;
    let returnFocus = null;

    const setSlide = (index) => {
      currentIndex = (index + items.length) % items.length;
      const item = items[currentIndex];
      const source = item.querySelector("img");
      const figure = item.closest("figure");
      const title = figure?.querySelector("figcaption strong")?.textContent?.trim() || source?.alt || "Prototype screen";
      const description = figure?.querySelector("figcaption p")?.textContent?.trim() || "";
      if (!source) {
        return;
      }

      image.src = item.href;
      image.alt = source.alt;
      image.width = Number(source.getAttribute("width")) || 1920;
      image.height = Number(source.getAttribute("height")) || 1200;
      counter.textContent = `${String(currentIndex + 1).padStart(2, "0")} / ${String(items.length).padStart(2, "0")}`;
      label.textContent = title;
      summary.textContent = description;
      status.textContent = `Screenshot ${currentIndex + 1} of ${items.length}: ${title}.`;
      previousButton.setAttribute("aria-label", `Show previous screenshot before ${title}`);
      nextButton.setAttribute("aria-label", `Show next screenshot after ${title}`);
    };

    const move = (offset) => setSlide(currentIndex + offset);

    items.forEach((item, index) => {
      item.addEventListener("click", (event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
          return;
        }
        event.preventDefault();
        returnFocus = item;
        setSlide(index);
        gallery.showModal();
        closeButton.focus();
      });
    });

    previousButton.addEventListener("click", () => move(-1));
    nextButton.addEventListener("click", () => move(1));
    closeButton.addEventListener("click", () => gallery.close());
    gallery.addEventListener("click", (event) => {
      if (event.target === gallery) {
        gallery.close();
      }
    });
    gallery.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        move(-1);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        move(1);
      }
    });
    gallery.addEventListener("close", () => {
      if (returnFocus?.isConnected) {
        returnFocus.focus();
      }
      returnFocus = null;
    });
  }

  function initBreadcrumbs() {
    const path = relativePath();
    const heroInner = document.querySelector(".article-hero-inner, .error-hero-inner");
    if (!path || !heroInner || heroInner.querySelector(".breadcrumbs")) {
      return;
    }

    const label = routeLabels[path] || document.querySelector("h1")?.textContent?.trim() || "Current page";
    const crumbs = [["", "Home"]];
    if (path.startsWith("docs/") && path !== "docs/") {
      crumbs.push(["docs/", "Documentation"]);
    } else if (path.startsWith("tutorials/") && path !== "tutorials/") {
      crumbs.push(["tutorials/", "Tutorials"]);
    }
    crumbs.push([path, label]);

    const nav = document.createElement("nav");
    nav.className = "breadcrumbs";
    nav.setAttribute("aria-label", "Breadcrumb");
    const list = document.createElement("ol");

    crumbs.forEach(([route, text], index) => {
      const item = document.createElement("li");
      if (index === crumbs.length - 1) {
        const current = document.createElement("span");
        current.setAttribute("aria-current", "page");
        current.textContent = text;
        item.append(current);
      } else {
        const link = document.createElement("a");
        link.href = new URL(route, siteRoot).href;
        link.textContent = text;
        item.append(link);
      }
      list.append(item);
    });

    nav.append(list);
    heroInner.prepend(nav);
  }

  function classifyDocumentationLink(path) {
    const groups = [
      ["Start", ["docs/", "docs/foundations.html", "docs/prototype-walkthrough.html"]],
      ["Design", ["docs/model.html", "docs/getting-started.html", "tutorials/", "tutorials/first-application.html", "tutorials/reading-a-receipt.html"]],
      ["Operate", ["docs/lifecycle.html", "docs/governance.html", "docs/security-and-privacy.html", "docs/hosts-and-portability.html", "docs/platform-support.html"]],
      ["Evidence", ["docs/evidence-and-roadmap.html", "docs/reference.html", "docs/agent-kits.html", "papers/stateware-whitepaper-public-v1.1.html", "releases/"]],
    ];
    return groups.find(([, paths]) => paths.includes(path))?.[0] || "More";
  }

  function initDocumentationNavigation() {
    const aside = document.querySelector('.doc-sidebar[aria-label="Documentation sections"]');
    const nav = aside?.querySelector("nav");
    if (!aside || !nav) {
      return;
    }

    const anchors = [...nav.querySelectorAll(":scope > a")];
    if (anchors.length > 7) {
      const orderedGroups = ["Start", "Design", "Operate", "Evidence", "More"];
      const linksByGroup = new Map(orderedGroups.map((group) => [group, []]));
      anchors.forEach((anchor) => {
        linksByGroup.get(classifyDocumentationLink(relativePath(anchor.href))).push(anchor);
      });

      const fragment = document.createDocumentFragment();
      orderedGroups.forEach((group) => {
        const groupLinks = linksByGroup.get(group);
        if (!groupLinks.length) {
          return;
        }
        const wrapper = document.createElement("div");
        wrapper.className = "doc-nav-group";
        const heading = document.createElement("p");
        heading.className = "doc-nav-group-label";
        heading.textContent = group;
        const links = document.createElement("div");
        links.className = "doc-nav-group-links";
        groupLinks.forEach((link) => links.append(link));
        wrapper.append(heading, links);
        fragment.append(wrapper);
      });
      nav.replaceChildren(fragment);
    }

    if (nav.querySelectorAll("a").length < 6) {
      return;
    }

    aside.classList.add("doc-nav-enhanced");
    if (!nav.id) {
      nav.id = "documentation-navigation";
    }
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "doc-nav-toggle";
    toggle.setAttribute("aria-controls", nav.id);
    toggle.setAttribute("aria-expanded", "false");
    toggle.textContent = "Browse documentation";
    nav.dataset.open = "false";
    aside.insertBefore(toggle, nav);

    toggle.addEventListener("click", () => {
      const open = nav.dataset.open !== "true";
      nav.dataset.open = String(open);
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  function uniqueHeadingId(heading) {
    if (heading.id) {
      return heading.id;
    }
    const base = heading.textContent
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-") || "section";
    let candidate = base;
    let suffix = 2;
    while (document.getElementById(candidate)) {
      candidate = `${base}-${suffix}`;
      suffix += 1;
    }
    heading.id = candidate;
    return candidate;
  }

  function initPageTableOfContents() {
    const article = document.querySelector(".prose:not([data-no-toc])");
    if (!article || article.querySelector(".page-toc")) {
      return;
    }

    const headings = [...article.querySelectorAll(":scope > h2, :scope > h3")];
    if (headings.length < 3) {
      return;
    }

    const details = document.createElement("details");
    details.className = "page-toc";
    details.open = window.matchMedia("(min-width: 801px)").matches;
    const summary = document.createElement("summary");
    summary.textContent = "On this page";
    const list = document.createElement("ol");
    const linksById = new Map();

    headings.forEach((heading) => {
      const id = uniqueHeadingId(heading);
      const item = document.createElement("li");
      item.dataset.level = heading.tagName.slice(1);
      const link = document.createElement("a");
      link.href = `#${id}`;
      link.textContent = heading.textContent.trim();
      link.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 800px)").matches) {
          details.open = false;
        }
      });
      item.append(link);
      list.append(item);
      linksById.set(id, link);
    });

    details.append(summary, list);
    const notice = article.querySelector(":scope > .notice--quiet");
    if (notice) {
      notice.insertAdjacentElement("afterend", details);
    } else {
      article.prepend(details);
    }

    if (!("IntersectionObserver" in window)) {
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (!visible) {
          return;
        }
        linksById.forEach((link) => link.removeAttribute("aria-current"));
        linksById.get(visible.target.id)?.setAttribute("aria-current", "location");
      },
      { rootMargin: "-15% 0px -72% 0px", threshold: [0, 1] },
    );
    headings.forEach((heading) => observer.observe(heading));
  }

  function initPagination() {
    const article = document.querySelector(".prose");
    if (!article || article.querySelector(".doc-pagination")) {
      return;
    }

    const path = relativePath();
    const sequence = path.startsWith("docs/")
      ? documentationSequence
      : path.startsWith("tutorials/")
        ? tutorialSequence
        : null;
    if (!sequence) {
      return;
    }

    const index = sequence.findIndex(([route]) => route === path);
    if (index <= 0) {
      return;
    }

    const pagination = document.createElement("nav");
    pagination.className = "doc-pagination";
    pagination.setAttribute("aria-label", "Previous and next pages");

    const createLink = (entry, direction) => {
      if (!entry) {
        const spacer = document.createElement("span");
        spacer.setAttribute("aria-hidden", "true");
        return spacer;
      }
      const [route, label] = entry;
      const link = document.createElement("a");
      link.href = new URL(route, siteRoot).href;
      const small = document.createElement("small");
      small.textContent = direction;
      const strong = document.createElement("strong");
      strong.textContent = label;
      link.append(small, strong);
      return link;
    };

    pagination.append(
      createLink(sequence[index - 1], "Previous"),
      createLink(sequence[index + 1], "Next"),
    );
    article.append(pagination);
  }

  async function copyText(text) {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.append(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    textarea.remove();
    if (!copied) {
      throw new Error("Copy command was rejected");
    }
  }

  function initCodeCopy() {
    const blocks = [...document.querySelectorAll(".prose pre, .code-panel")];
    if (!blocks.length) {
      return;
    }

    const status = document.createElement("p");
    status.className = "copy-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.hidden = true;
    document.body.append(status);
    let statusTimer = 0;

    blocks.forEach((block) => {
      if (block.querySelector(":scope > .copy-button")) {
        return;
      }
      const source = block.querySelector("code") || block;
      const text = source.textContent;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "copy-button";
      button.textContent = "Copy";
      button.setAttribute("aria-label", "Copy code to clipboard");
      button.addEventListener("click", async () => {
        try {
          await copyText(text);
          button.textContent = "Copied";
          status.textContent = "Code copied to the clipboard.";
        } catch {
          button.textContent = "Select";
          status.textContent = "Copy was unavailable. Select the code manually.";
        }
        status.hidden = false;
        window.clearTimeout(statusTimer);
        statusTimer = window.setTimeout(() => {
          button.textContent = "Copy";
          status.hidden = true;
        }, 2200);
      });
      block.append(button);
    });
  }

  function initDocumentationFilter() {
    const input = document.querySelector("[data-doc-filter]");
    const catalogue = document.querySelector("[data-doc-catalogue]");
    if (!input || !catalogue) {
      return;
    }

    const entries = [...catalogue.querySelectorAll("[data-doc-entry]")];
    const groups = [...catalogue.querySelectorAll(".docs-group")];
    const status = document.getElementById("documentation-filter-status");
    const empty = document.querySelector("[data-doc-filter-empty]");

    const applyFilter = () => {
      const query = input.value.trim().toLowerCase();
      let visibleCount = 0;
      entries.forEach((entry) => {
        const haystack = `${entry.textContent} ${entry.dataset.keywords || ""}`.toLowerCase();
        const visible = !query || haystack.includes(query);
        entry.hidden = !visible;
        if (visible) {
          visibleCount += 1;
        }
      });
      groups.forEach((group) => {
        group.hidden = !group.querySelector("[data-doc-entry]:not([hidden])");
      });
      if (status) {
        status.textContent = query ? `${visibleCount} topic${visibleCount === 1 ? "" : "s"} shown.` : "";
      }
      if (empty) {
        empty.hidden = visibleCount !== 0;
      }
    };

    input.addEventListener("input", applyFilter);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && input.value) {
        input.value = "";
        applyFilter();
      }
    });
  }

  function initFooterNavigation() {
    const footer = document.querySelector(".footer-inner");
    if (!footer || footer.querySelector(".footer-nav")) {
      return;
    }
    const nav = document.createElement("nav");
    nav.className = "footer-nav";
    nav.setAttribute("aria-label", "Footer navigation");
    [
      ["docs/", "Docs"],
      ["tutorials/", "Tutorials"],
      ["releases/", "Release status"],
    ].forEach(([route, label]) => {
      const link = document.createElement("a");
      link.href = new URL(route, siteRoot).href;
      link.textContent = label;
      nav.append(link);
    });
    const meta = footer.querySelector(".footer-meta");
    footer.insertBefore(nav, meta || null);
  }

  function setCurrentYear() {
    document.querySelectorAll("[data-current-year]").forEach((element) => {
      element.textContent = String(new Date().getFullYear());
    });
  }

  try {
    ensureEnhancementStyles();
    initPrimaryNavigation();
    initReveals();
    initAtlasParallax();
    initPrototypeGallery();
    initBreadcrumbs();
    initDocumentationNavigation();
    initPageTableOfContents();
    initPagination();
    initCodeCopy();
    initDocumentationFilter();
    initFooterNavigation();
    setCurrentYear();
  } catch (error) {
    document.querySelectorAll(".reveal").forEach((element) => element.classList.add("is-visible"));
    console.error("StatePort progressive enhancements failed.", error);
  }
})();
