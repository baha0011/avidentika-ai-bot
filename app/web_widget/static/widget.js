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
  const input = root.querySelector("textarea");
  const form = root.querySelector(".av-form");
  let session = localStorage.getItem("avidentika_session_id") || "";
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
      b.onclick = () => label.toLowerCase().includes("запис") ? showAppointment() : label.toLowerCase().includes("администратор") ? showSupport() : ask(label);
      quick.appendChild(b);
    });
  }
  async function sid() {
    if (session) return session;
    const r = await fetch(`${api}/api/session`);
    const d = await r.json();
    session = d.session_id;
    localStorage.setItem("avidentika_session_id", session);
    return session;
  }
  async function ask(text) {
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
    form.dataset.kind = "appointment";
    form.classList.add("av-open");
    form.innerHTML = `<input name="patient_name" placeholder="Имя пациента" required><input name="phone" placeholder="Телефон +380XXXXXXXXX" required><input name="telegram_username" placeholder="Telegram username"><input name="service" placeholder="Услуга" required><input name="preferred_date" placeholder="Желаемая дата"><input name="preferred_time" placeholder="Желаемое время"><input name="doctor" placeholder="Врач"><textarea name="comment" placeholder="Комментарий"></textarea><button class="av-submit" type="submit">Отправить заявку</button>`;
  }
  function showSupport() {
    form.dataset.kind = "support";
    form.classList.add("av-open");
    form.innerHTML = `<input name="patient_name" placeholder="Имя" required><input name="phone" placeholder="Телефон +380XXXXXXXXX" required><input name="telegram_username" placeholder="Telegram username"><textarea name="question" placeholder="Ваш вопрос" required></textarea><button class="av-submit" type="submit">Передать администратору</button>`;
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
      form.classList.remove("av-open");
      msg(`${d.message}\nНомер: ${d.public_id}`);
    } catch {
      msg("Заявку не удалось отправить. Проверьте номер телефона или попробуйте позже.", "bot", "av-error");
    }
  };
  root.querySelector(".av-chat-button").onclick = () => win.classList.toggle("av-open");
  root.querySelector(".av-send").onclick = () => ask(input.value);
  input.onkeydown = e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(input.value); } };
  buttons();
  msg("Здравствуйте! Я могу сориентировать по услугам, врачам, ценам, адресу и помочь оставить предварительную заявку.");
})();
