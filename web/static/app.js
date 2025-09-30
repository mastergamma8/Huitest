// Helpers
const fmt = (n) => "$" + n.toLocaleString("en-US");

const ITEMS = [
  { name: "Суперкар", price: 250000 },
  { name: "Яхта на сутки", price: 120000 },
  { name: "Рояль Steinway", price: 180000 },
  { name: "Полет на частном джете", price: 150000 },
  { name: "Часы люкс", price: 90000 },
  { name: "Алмазы", price: 50000 },
  { name: "VIP-тур по миру", price: 220000 },
  { name: "Современное искусство", price: 130000 },
  { name: "Ужин с шеф-поваром", price: 25000 },
  { name: "Пентхаус-аренда (неделя)", price: 300000 },
  { name: "Пожертвование фонду", price: 10000 },
  { name: "Золотая карта клуба", price: 45000 },
];

let tg = window.Telegram?.WebApp;
if (tg) {
  tg.expand();
  tg.setHeaderColor("secondary_bg_color");
  tg.setBackgroundColor("#0b1020");
}

let state = {
  sessionId: null,
  expiresAt: 0,
  nowOffset: 0, // server-now - client-now
  spent: 0,
  remaining: 1000000,
  ticking: false,
  user: tg?.initDataUnsafe?.user || null,
  initData: tg?.initData || ""
};

const userBox = document.getElementById("userBox");
if (state.user) {
  userBox.textContent = state.user.username ? "@" + state.user.username : (state.user.first_name || "Игрок");
}

const timeLeftEl = document.getElementById("timeLeft");
const progressEl = document.getElementById("progress");
const spentEl = document.getElementById("spent");
const remainingEl = document.getElementById("remaining");
const gridEl = document.getElementById("itemsGrid");
const logEl = document.getElementById("log");
const leaderEl = document.getElementById("leader");
const finishBtn = document.getElementById("finishBtn");

function renderItems() {
  gridEl.innerHTML = "";
  ITEMS.forEach((it, idx) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h4>${it.name}</h4>
      <div class="row">
        <div>${fmt(it.price)}</div>
        <div class="qty">
          <input type="number" min="1" value="1" id="qty-${idx}" />
          <button class="btn" data-idx="${idx}" data-m="1">x1</button>
          <button class="btn" data-idx="${idx}" data-m="10">x10</button>
          <button class="btn" data-idx="${idx}" data-m="100">x100</button>
        </div>
      </div>
      <button class="primary" data-buy="${idx}">Купить</button>
    `;
    gridEl.appendChild(card);
  });

  gridEl.addEventListener("click", (e) => {
    const t = e.target;
    if (t.dataset.m && t.dataset.idx) {
      const q = document.getElementById("qty-" + t.dataset.idx);
      q.value = parseInt(q.value || "1") * parseInt(t.dataset.m);
    } else if (t.dataset.buy) {
      const idx = parseInt(t.dataset.buy);
      const q = document.getElementById("qty-" + idx);
      const qty = Math.max(1, parseInt(q.value || "1"));
      buy(ITEMS[idx], qty);
    }
  });
}

function serverNow() {
  return Math.floor(Date.now() / 1000) + state.nowOffset;
}

function tick() {
  if (!state.ticking) return;
  const left = Math.max(0, state.expiresAt - serverNow());
  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");
  timeLeftEl.textContent = `${mm}:${ss}`;

  const p = Math.max(0, Math.min(100, (left / 300) * 100));
  progressEl.style.width = p + "%";

  if (left <= 0) {
    state.ticking = false;
    finish(true);
  } else {
    setTimeout(tick, 250);
  }
}

async function startSession() {
  const res = await fetch("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      initData: state.initData,
      user: state.user
    })
  });
  if (!res.ok) {
    alert("Не удалось стартовать сессию. Открой бота из Telegram.");
    return;
  }
  const data = await res.json();
  state.sessionId = data.session_id;
  state.spent = data.spent;
  state.expiresAt = data.expires_at;
  const clientNow = Math.floor(Date.now() / 1000);
  state.nowOffset = data.now - clientNow;
  updateMoney();
  state.ticking = true;
  tick();
  fetchTop();
}

function updateMoney() {
  spentEl.textContent = fmt(state.spent);
  state.remaining = Math.max(0, 1000000 - state.spent);
  remainingEl.textContent = fmt(state.remaining);
}

function appendLog(name, total) {
  const li = document.createElement("li");
  li.textContent = `${name} — ${fmt(total)}`;
  logEl.prepend(li);
}

async function buy(item, qty) {
  if (!state.sessionId) return;
  const total = item.price * qty;
  if (total <= 0) return;

  const res = await fetch("/api/spend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      initData: state.initData,
      user: state.user,
      session_id: state.sessionId,
      item: item.name + (qty>1 ? ` x${qty}` : ""),
      amount: total
    })
  });
  const data = await res.json();
  if (!data.ok) {
    if (data.reason) alert(data.reason);
    return;
  }
  state.spent = data.spent;
  updateMoney();
  appendLog(item.name + (qty>1?` x${qty}`:""), total);

  if (data.finished) {
    state.ticking = false;
    await finish(false);
  }
}

async function finish(byTimeout) {
  if (!state.sessionId) return;
  try {
    await fetch("/api/finish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        initData: state.initData,
        user: state.user,
        session_id: state.sessionId
      })
    });
  } catch(e) {}
  await fetchTop();
  const spent = state.spent;
  const msg = byTimeout
    ? `⏱️ Время вышло! Ты успел потратить ${fmt(spent)}.`
    : `🏁 Игра окончена! Потрачено ${fmt(spent)}.`;
  alert(msg);
  if (tg?.MainButton) {
    tg.MainButton.setText("Поделиться результатом");
    tg.MainButton.show();
    tg.MainButton.onClick(() => {
      tg.openTelegramLink(`https://t.me/share/url?text=${encodeURIComponent("Я потратил " + fmt(spent) + " за 5 минут! Попробуешь обогнать?")}`);
    });
  }
}

async function fetchTop() {
  const res = await fetch("/api/leaderboard");
  const data = await res.json();
  if (!data.ok) return;
  leaderEl.innerHTML = "";
  data.items.forEach((it, i) => {
    const li = document.createElement("li");
    li.textContent = `${i+1}. ${it.username || "anon"} — ${fmt(it.spent)}`;
    leaderEl.appendChild(li);
  });
}

finishBtn.addEventListener("click", () => finish(false));
renderItems();
startSession();
