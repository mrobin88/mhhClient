const assets = [
  seed("Apple", "AAPL", "stock", 227.48, 5, "up"),
  seed("Tesla", "TSLA", "stock", 248.91, 10, "volatile"),
  seed("Charizard ex", "PKMN-SV3-223", "collectible", 312.5, 10, "up"),
  seed("Black Lotus", "MTG-LEA-232", "collectible", 18400, 10, "down"),
];

let filter = "all";
let tier = "free";
let defaultThreshold = 5;
const alerts = [];

function seed(name, symbol, category, price, threshold, trend) {
  const history = [];
  let value = price;
  for (let i = 35; i >= 0; i--) {
    const drift = trend === "up" ? 0.004 : trend === "down" ? -0.003 : i % 5 === 0 ? 0.02 : -0.008;
    value = Math.max(0.01, value / (1 + drift + (Math.random() - 0.5) * 0.02));
    history.unshift({ t: Date.now() - i * 15 * 60 * 1000, p: value });
  }
  history[history.length - 1] = { t: Date.now(), p: price };
  return { id: symbol, name, symbol, category, price, threshold, history };
}

function percent(from, to) {
  return from === 0 ? 0 : ((to - from) / Math.abs(from)) * 100;
}

function latestJump(asset) {
  const h = asset.history;
  if (h.length < 2) return 0;
  return percent(h[h.length - 2].p, h[h.length - 1].p);
}

function sessionChange(asset) {
  return percent(asset.history[0].p, asset.price);
}

function money(n) {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function sparkline(history, color) {
  const w = 140;
  const h = 52;
  const prices = history.map((x) => x.p);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const span = max - min || 1;
  const pts = history
    .map((x, i) => {
      const px = (i / (history.length - 1)) * w;
      const py = h - ((x.p - min) / span) * (h - 6) - 3;
      return `${px},${py}`;
    })
    .join(" ");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline fill="none" stroke="${color}" stroke-width="2" points="${pts}" /></svg>`;
}

function render() {
  const visible = assets.filter((a) => filter === "all" || a.category === filter);
  const hot = assets.filter((a) => Math.abs(latestJump(a)) >= a.threshold).length;

  document.getElementById("tierName").textContent = tier === "instant" ? "Instant Scout" : "Free";
  document.getElementById("tierCopy").textContent =
    tier === "instant" ? "Real-time alerts" : "Alerts delayed 2–4 hours";
  document.getElementById("hotCount").textContent = `${hot} hot`;
  document.getElementById("paywallBtn").textContent = tier === "instant" ? "⚡" : "⏱";

  document.getElementById("filters").innerHTML = ["all", "stock", "collectible"]
    .map((key) => {
      const label = key === "all" ? "All" : key === "stock" ? "Stocks" : "Collectibles";
      return `<button class="chip ${filter === key ? "active" : ""}" data-filter="${key}">${label}</button>`;
    })
    .join("");

  document.getElementById("assets").innerHTML = visible
    .map((asset) => {
      const jump = latestJump(asset);
      const breached = Math.abs(jump) >= asset.threshold;
      const color = sessionChange(asset) >= 0 ? "#38f2a8" : "#ff547a";
      return `
        <article class="card ${breached ? "hot-card" : ""}" data-id="${asset.id}">
          <div class="row">
            <div>
              <p class="symbol">${asset.symbol}</p>
              <p class="name">${asset.name}</p>
            </div>
            <span class="cat ${asset.category}">${asset.category.toUpperCase()}</span>
          </div>
          <div class="row">
            <div>
              <p class="price">${money(asset.price)}</p>
              <div>
                <span class="jump ${jump >= 0 ? "up" : "down"}">${jump >= 0 ? "+" : ""}${jump.toFixed(1)}%</span>
                ${breached ? `<span class="badge ${jump >= 0 ? "" : "down"}">ALERT</span>` : ""}
              </div>
            </div>
            ${sparkline(asset.history, color)}
          </div>
          <div class="meta">
            <span>Alert at ${asset.threshold}%</span>
            <span class="${sessionChange(asset) >= 0 ? "up" : "down"}">${sessionChange(asset) >= 0 ? "+" : ""}${sessionChange(asset).toFixed(1)}% session</span>
          </div>
        </article>`;
    })
    .join("");
}

function toast(message) {
  const el = document.getElementById("toast");
  el.hidden = false;
  el.textContent = message;
  setTimeout(() => {
    el.hidden = true;
  }, 3200);
}

function tick() {
  for (const asset of assets) {
    const base = asset.category === "collectible" ? 0.035 : 0.016;
    const spiked = Math.random() < (asset.category === "collectible" ? 0.14 : 0.09);
    const mag = spiked ? 0.06 + Math.random() * 0.12 : Math.random() * base;
    const next = Math.max(0.01, asset.price * (1 + mag * (spiked || Math.random() > 0.5 ? 1 : -1)));
    asset.price = next;
    asset.history.push({ t: Date.now(), p: next });
    if (asset.history.length > 80) asset.history.shift();

    const jump = latestJump(asset);
    if (Math.abs(jump) >= asset.threshold) {
      const delay = tier === "instant" ? 400 : 15000;
      const text = jump >= 0
        ? `🚨 Price Jump! ${asset.name} has spiked by ${Math.abs(jump).toFixed(1)}%!`
        : `📉 Price Drop! ${asset.name} has fallen by ${Math.abs(jump).toFixed(1)}%!`;
      if (!alerts.includes(asset.id + jump.toFixed(2))) {
        alerts.push(asset.id + jump.toFixed(2));
        setTimeout(() => toast(text), delay);
      }
    }
  }
  render();
}

function openDetail(id) {
  const asset = assets.find((a) => a.id === id);
  if (!asset) return;
  const jump = latestJump(asset);
  document.getElementById("detail").innerHTML = `
    <p class="kicker">${asset.symbol}</p>
    <h2>${asset.name}</h2>
    <div class="detail-price">${money(asset.price)}</div>
    <p class="${jump >= 0 ? "up" : "down"}">Last tick ${jump >= 0 ? "+" : ""}${jump.toFixed(2)}%</p>
    ${sparkline(asset.history, sessionChange(asset) >= 0 ? "#38f2a8" : "#ff547a")}
    <div class="stats">
      <div class="stat"><span>CATEGORY</span>${asset.category}</div>
      <div class="stat"><span>THRESHOLD</span>${asset.threshold}%</div>
      <div class="stat"><span>SESSION</span>${sessionChange(asset).toFixed(1)}%</div>
    </div>
  `;
  document.getElementById("detailModal").showModal();
}

document.getElementById("filters").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-filter]");
  if (!btn) return;
  filter = btn.dataset.filter;
  render();
});

document.getElementById("assets").addEventListener("click", (e) => {
  const card = e.target.closest("[data-id]");
  if (card) openDetail(card.dataset.id);
});

const slider = document.getElementById("thresholdSlider");
const thresholdValue = document.getElementById("thresholdValue");
slider.addEventListener("input", () => {
  thresholdValue.textContent = `${slider.value}%`;
  document.querySelectorAll("[data-preset]").forEach((b) => {
    b.classList.toggle("active", b.dataset.preset === slider.value);
  });
});
document.querySelector(".presets").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-preset]");
  if (!btn) return;
  slider.value = btn.dataset.preset;
  slider.dispatchEvent(new Event("input"));
});
document.getElementById("saveThreshold").addEventListener("click", () => {
  defaultThreshold = Number(slider.value);
  if (document.getElementById("applyAll").checked) {
    assets.forEach((a) => {
      a.threshold = defaultThreshold;
    });
  }
  document.getElementById("thresholdModal").close();
  render();
});

document.getElementById("thresholdBtn").onclick = () => {
  slider.value = defaultThreshold;
  slider.dispatchEvent(new Event("input"));
  document.getElementById("thresholdModal").showModal();
};
document.getElementById("closeThreshold").onclick = () => document.getElementById("thresholdModal").close();
document.getElementById("paywallBtn").onclick = () => {
  document.getElementById("freeCard").classList.toggle("active", tier === "free");
  document.getElementById("scoutCard").classList.toggle("active", tier === "instant");
  document.getElementById("unlockBtn").textContent =
    tier === "instant" ? "Back to Free (demo)" : "Unlock Instant Scout — $4.99/mo";
  document.getElementById("paywallModal").showModal();
};
document.getElementById("unlockBtn").onclick = () => {
  tier = tier === "instant" ? "free" : "instant";
  document.getElementById("paywallModal").close();
  render();
};
document.getElementById("closePaywall").onclick = () => document.getElementById("paywallModal").close();
document.getElementById("closeDetail").onclick = () => document.getElementById("detailModal").close();

render();
setInterval(tick, 4000);
