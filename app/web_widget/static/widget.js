(() => {
  const s = document.currentScript;
  const api = (s?.dataset.apiBase || window.location.origin).replace(/\/$/, "");
  const css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = s?.dataset.css || `${api}/static/widget.css`;
  document.head.appendChild(css);

  const root = document.createElement("div");
  root.innerHTML = `<button class="av-chat-button">💬</button><section class="av-chat-window"><header class="av-chat-header"><div class="av-chat-title">AI-помощник AVIDENTIKA</div><div class="av-chat-subtitle">Я могу сориентировать по информации клиники. Окончательную консультацию проводит врач.</div></header><div class="av-chat-messages"></div><div class="av-quick"></div><form class="av-form"></form><div class="av-input-row"><textarea maxlength="1500" placeholder="Напишите вопрос..."></textarea><button class="av-send" type="button">➤</button></div></section>`;
  document.body.appendChild(root);

  const win = root.querySelector(".av-chat-window");
  const messages = root.querySelector(".av-chat-messages");
  const quick = root.querySelector(".av-quick");
  const inputRow = root.querySelector(".av-input-row");
  const input = root.querySelector(".av-input-row textarea");
  const form = root.querySelector(".av-form");
  let session = localStorage.getItem("avidentika_session_id") || "";
  let lastNoticeId = Number(localStorage.getItem("avidentika_last_notice_id") || "0");
  const actions = ["Записаться на приём", "Задать вопрос", "Связаться с администратором", "Услуги", "Врачи", "Цены", "Контакты"];

  function msg(text, who = "bot", extra = "") {
    const el = document.createElement("div");
    el.className = `av-msg av-${who} ${extra}`;
    el.textContent = text;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }
  function buttons(list = actions) {
    quick.innerHTML = "";
    list.forEach(label => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      b.onclick = () => handleQuick(label);
      quick.appendChild(b);
    });
  }
  function handleQuick(label) {
    const lower = label.toLowerCase();
    if (lower.includes("запис")) return showAppointment();
    if (lower.includes("администратор")) return showSupport();
    closeForm(false);
    ask(label);
  }
  function closeForm(showNotice = true) {
    if (!form.classList.contains("av-open")) return;
    form.classList.remove("av-open");
    form.innerHTML = "";
    inputRow.classList.remove("av-hidden");
    if (showNotice) msg("Форма закрыта. Можете задать вопрос или выбрать другое действие.");
  }
  function openForm(kind, html) {
    form.dataset.kind = kind;
    form.innerHTML = html;
    form.classList.add("av-open");
    inputRow.classList.add("av-hidden");
    form.querySelector(".av-cancel")?.addEventListener("click", () => closeForm(true));
    form.querySelector("input, textarea")?.focus();
  }
  async function sid() {
    if (session) return session;
    const r = await fetch(`${api}/api/session`);
    const d = await r.json();
    session = d.session_id;
    localStorage.setItem("avidentika_session_id", session);
    return session;
  }
  async function pollNotices() {
    try {
      await sid();
      const r = await fetch(`${api}/api/notifications?session_id=${encodeURIComponent(session)}&after_id=${lastNoticeId}`);
      if (!r.ok) return;
      const d = await r.json();
      (d.notifications || []).forEach(n => {
        if (Number(n.id) > lastNoticeId) {
          lastNoticeId = Number(n.id);
          localStorage.setItem("avidentika_last_notice_id", String(lastNoticeId));
        }
        msg(n.message, "bot", "av-notice");
      });
    } catch {}
  }
  async function ask(text) {
    closeForm(false);
    text = text.trim();
    if (!text) return;
    await sid();
    msg(text, "user");
    input.value = "";
    const t = msg("Печатает...");
    try {
      const r = await fetch(`${api}/api/chat`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({session_id: session, message: text, language: "auto"})});
      if (!r.ok) throw new Error("bad");
      const d = await r.json();
      t.textContent = d.answer;
      buttons(d.quick_actions?.length ? d.quick_actions : actions);
    } catch {
      t.textContent = "Не удалось связаться с помощником. Попробуйте позже или позвоните в клинику.";
      t.classList.add("av-error");
    }
  }
  function showAppointment() {
    openForm("appointment", `<div class="av-form-head"><strong>Предварительная запись</strong><button class="av-cancel" type="button">Отмена</button></div><input name="patient_name" placeholder="Имя пациента" required><input name="phone" placeholder="Телефон +380XXXXXXXXX" required><input name="telegram_username" placeholder="Telegram username"><input name="service" placeholder="Услуга" required><input name="preferred_date" placeholder="Желаемая дата"><input name="preferred_time" placeholder="Желаемое время"><input name="doctor" placeholder="Врач"><textarea name="comment" placeholder="Комментарий"></textarea><button class="av-submit" type="submit">Отправить заявку</button>`);
  }
  function showSupport() {
    openForm("support", `<div class="av-form-head"><strong>Связь с администратором</strong><button class="av-cancel" type="button">Отмена</button></div><input name="patient_name" placeholder="Имя" required><input name="phone" placeholder="Телефон +380XXXXXXXXX" required><input name="telegram_username" placeholder="Telegram username"><textarea name="question" placeholder="Ваш вопрос" required></textarea><button class="av-submit" type="submit">Передать администратору</button>`);
  }
  form.onsubmit = async (e) => {
    e.preventDefault();
    await sid();
    const data = Object.fromEntries(new FormData(form).entries());
    data.session_id = session;
    data.created_from_url = location.href;
    const endpoint = form.dataset.kind === "support" ? "/api/support" : "/api/appointments";
    try {
      const r = await fetch(`${api}${endpoint}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
      if (!r.ok) throw new Error("bad");
      const d = await r.json();
      closeForm(false);
      msg(`${d.message}\nНомер: ${d.public_id}`);
    } catch {
      msg("Заявку не удалось отправить. Проверьте номер телефона или попробуйте позже.", "bot", "av-error");
    }
  };
  root.querySelector(".av-chat-button").onclick = () => { win.classList.toggle("av-open"); pollNotices(); };
  root.querySelector(".av-send").onclick = () => ask(input.value);
  input.onkeydown = e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(input.value); } };
  buttons();
  msg("Здравствуйте! Я могу сориентировать по услугам, врачам, ценам, адресу и помочь оставить предварительную заявку.");
  setInterval(() => { if (win.classList.contains("av-open")) pollNotices(); }, 7000);
})();
