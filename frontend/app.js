/* Learning Buddy - student UI (vanilla JS, no external dependencies) */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (x) => (x == null ? "n/a" : Math.round(x * 100) + "%");
const STATUS = {
  demonstrated: ["Demonstrated", "ok"], completed_not_demonstrated: ["Completed, not yet demonstrated", "info"],
  in_progress: ["In progress", "warn"], gap: ["Gap", "bad"],
};
const state = { sid: null, dash: null, kb: null, session: localGet("chatSession") || null, week: 1, practice: null, quiz: null };

function localGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function localSet(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } }

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch { /* not json */ }
    throw new Error(msg);
  }
  return res.json();
}
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 3200); }

/* ------------------------------------------------------------ boot */
async function boot() {
  state.kb = await api("/api/kb/summary");
  const students = await api("/api/students");
  const sel = $("#studentSelect");
  sel.innerHTML = students.map((s) => `<option value="${esc(s.id)}">${esc(s.id)} - ${esc(s.name)} (${esc(s.programme)} Y${s.year}${s.goal_id ? ", " + esc(goalName(s.goal_id)) : ""})</option>`).join("");
  sel.onchange = () => selectStudent(sel.value);
  const want = new URLSearchParams(location.search).get("sid") || localGet("sid") || "S1024";
  const sid = students.some((s) => s.id === want) ? want : students[0]?.id;
  if (sid) { sel.value = sid; await selectStudent(sid); }
  const tab = location.hash.slice(1);
  if (tab && $("#tab-" + tab)) showTab(tab);
  $$("#tabs button").forEach((b) => (b.onclick = () => showTab(b.dataset.tab)));
  $("#newStudentBtn").onclick = openOnboarding;
  $("#chatForm").onsubmit = (e) => { e.preventDefault(); sendChat($("#chatInput").value); };
  $("#newSessionBtn").onclick = () => { state.session = null; localSet("chatSession", ""); $("#chatLog").innerHTML = ""; greet(); };
  setupOnboarding();
}
const goalName = (id) => state.kb?.goals.find((g) => g.id === id)?.name || id;
const skillName = (id) => state.kb?.skills.find((s) => s.id === id)?.name || id;
const course = (code) => state.kb?.courses.find((c) => c.code === code);

function showTab(name) {
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  $$(".tab").forEach((t) => t.classList.toggle("active", t.id === "tab-" + name));
  $("#chat").classList.toggle("active", name === "chat");
  if (name === "history") renderHistory();
}

async function selectStudent(sid) {
  state.sid = sid; localSet("sid", sid);
  if (localGet("chatSid") !== sid) { state.session = null; localSet("chatSession", ""); localSet("chatSid", sid); }
  await refresh();
  await loadChat();
}

async function refresh() {
  state.dash = await api(`/api/students/${state.sid}/dashboard`);
  renderOverview(); renderPlan(); renderLearn(); renderAssess(); renderAdapt();
  $("#chatMode").textContent = state.dash.llm_configured ? "" : "(offline mode: rule-based replies)";
}

/* ------------------------------------------------------------ overview */
function skillRow(g) {
  const [label, cls] = STATUS[g.status] || [g.status, ""];
  const fillCls = g.status === "demonstrated" ? "ok" : g.status === "gap" ? "bad" : g.status === "in_progress" ? "warn" : "";
  const ev = (g.evidence || []).slice(-3).map((e) => `${e.source}: ${e.detail || ""} (${pct(e.score)})`).join("\n");
  return `<div class="skill" title="${esc(ev || "No evidence yet")}">
    <div><strong>${esc(g.name)}</strong><div class="small muted">${pct(g.mastery)} of ${pct(g.target)} target - confidence ${pct(g.confidence)}</div></div>
    <div class="bar" aria-label="mastery ${pct(g.mastery)}"><div class="fill ${fillCls}" style="width:${Math.min(100, g.mastery * 100)}%"></div><div class="target" style="left:${g.target * 100}%"></div></div>
    <div><span class="badge ${cls}">${esc(label)}</span>${g.struggling ? ' <span class="badge bad">struggling</span>' : ""}${!g.tested ? ' <span class="badge">untested</span>' : ""}</div></div>`;
}

function renderOverview() {
  const d = state.dash, dg = d.diagnosis, s = d.student, p = d.plan;
  const el = $("#tab-overview");
  if (dg.goal_is_vague) {
    el.innerHTML = `<div class="card"><h2>Hi ${esc(s.name)} - let's pin down your goal</h2>
      <p>You said: <em>"${esc(s.goal_text || "nothing yet")}"</em>. A clear goal lets me plan courses, practice and milestones.</p>
      <p>Goals that fit your current skills best:</p>
      <div class="row">${(dg.goal_candidates.length ? dg.goal_candidates : dg.goal_fit).slice(0, 4).map((g) =>
        `<button class="btn ghost" data-goal="${esc(g.goal)}">${esc(g.name)}${g.readiness != null ? ` (${pct(g.readiness)} ready)` : ""}</button>`).join("")}</div>
      <p class="small muted">Not sure? Ask the buddy, e.g. "I like coding but also economics".</p></div>`;
    $$("[data-goal]", el).forEach((b) => (b.onclick = () => override({ type: "change_goal", goal: b.dataset.goal })));
    return;
  }
  const next = p.learning_track.weeks.find((w) => w.items.length);
  const ready = Math.round((dg.readiness || 0) * 100), proj = Math.round((p.readiness_projected || 0) * 100);
  el.innerHTML = `
  <div class="row">
    <div class="card"><h2>${esc(dg.goal.name)}</h2>
      <div class="ready"><div class="ring" style="--p:${ready}"><span>${ready}%</span></div>
        <div><div>Goal readiness today</div><div class="muted small">Projected <strong>${proj}%</strong> if you follow plan v${d.plan_version}</div>
        <div class="small muted">${esc(s.name)} - ${esc(s.programme)} year ${s.year} - CGPA ${s.cgpa} - planning semester ${s.current_semester}</div></div></div>
    </div>
    <div class="card"><h3>What to do next</h3>
      ${next ? `<p><strong>${esc(next.items[0].title)}</strong><br><span class="small muted">${esc(next.items[0].why || "")}</span></p>
        <button class="btn small" onclick="showTab('learn')">Open this week</button>` : "<p>You're all caught up for this semester.</p>"}
      ${p.semesters[0] ? `<p class="small">Next semester: ${p.semesters[0].courses.filter((c) => c.code).map((c) => `<span class="code">${esc(c.code)}</span>`).join(", ")}</p>` : ""}
    </div>
  </div>
  ${dg.mismatches.map((m) => `<div class="alert warn"><strong>Heads-up:</strong> ${esc(m.message)}
     <button class="btn small ghost" data-reassess>Reassess my goal</button></div>`).join("")}
  <div class="card" id="reassess" hidden><h3>How well do other goals fit right now?</h3>
     ${dg.goal_fit.map((g) => `<div class="skill"><div>${esc(g.name)}</div><div class="bar"><div class="fill" style="width:${g.readiness * 100}%"></div></div>
       <div>${g.goal === dg.goal.id ? '<span class="badge brand">current</span>' : `<button class="btn small ghost" data-goal="${esc(g.goal)}">Switch</button>`}</div></div>`).join("")}
     <p class="small muted">Readiness compares your evidence with each goal's required skills. Switching re-plans immediately; you can switch back any time.</p></div>
  <div class="card"><h3>Skills your goal needs</h3>
    <p class="small muted">Bar = estimated mastery; line = target. "Demonstrated" needs tested evidence (quiz, exercise, project, mock), not only a course grade or self-rating. Hover a row to see the evidence.</p>
    ${dg.gaps.map(skillRow).join("")}</div>
  <div class="row">
    <div class="card"><h3>Strengths</h3>${dg.strengths.length ? dg.strengths.map((x) => `<span class="badge ok">${esc(x.name)} ${pct(x.mastery)}</span> `).join("") : '<p class="muted small">Take the diagnostic to discover them.</p>'}</div>
    <div class="card"><h3>Needs work</h3>${dg.weaknesses.length ? dg.weaknesses.map((x) => `<span class="badge bad">${esc(x.name)} ${pct(x.mastery)}</span> `).join("") : '<p class="muted small">No tested weaknesses yet.</p>'}</div>
  </div>
  <div class="card"><h3>Mastery criteria for this goal</h3><ul>${(p.mastery_criteria || []).map((c) => `<li>${esc(c)}</li>`).join("")}</ul>
    <p class="small muted">Course completion alone does not count: these are checked with timed mocks, projects and interviews (record them in Assess).</p></div>`;
  $$("[data-reassess]", el).forEach((b) => (b.onclick = () => { $("#reassess").hidden = false; $("#reassess").scrollIntoView({ behavior: "smooth" }); }));
  $$("[data-goal]", el).forEach((b) => (b.onclick = () => override({ type: "change_goal", goal: b.dataset.goal })));
}

/* ------------------------------------------------------------ plan */
function renderPlan() {
  const d = state.dash, p = d.plan, v = d.validation;
  const el = $("#tab-plan");
  if (!p.goal) { el.innerHTML = `<div class="card"><p>Set a goal first (Overview tab or chat) and your plan appears here.</p></div>`; return; }
  const slotBadge = { core: "brand", backlog: "bad", open_elective: "info", dept_elective: "info", extra: "warn", minor: "ok" };
  el.innerHTML = `
  <div class="card"><div class="row" style="align-items:center;justify-content:space-between">
    <div><h2 style="margin:0">Plan v${d.plan_version}</h2><div class="small muted">${esc(d.plan_reason)}</div></div>
    <div>${v.passed ? `<span class="badge ok">All ${v.n_checks} checks passed</span>` : `<span class="badge bad">${v.n_failed} checks failed</span>`}
      <button class="btn small ghost" id="toggleChecks">Show checks</button></div></div>
    <ul class="checks" id="checks" hidden>${v.checks.map((c) => `<li>${c.passed ? "&#10004;" : c.severity === "warning" ? "&#9888;" : "&#10008;"} ${esc(c.name)}
      ${c.details.length ? `<div class="small muted">${c.details.map(esc).join("; ")}</div>` : ""}</li>`).join("")}</ul>
    ${d.plan_diff && d.plan_diff.changes && !d.plan_diff.first_version ? `<div class="alert info"><strong>What changed in v${d.plan_version}:</strong><ul class="diff">${d.plan_diff.changes.map((c) => `<li>${esc(c)}</li>`).join("")}</ul></div>` : ""}
    ${(p.infeasible || []).map((i) => `<div class="alert bad"><strong>Not possible:</strong> ${esc(i.message)}</div>`).join("")}
    ${(p.notes || []).map((n) => `<div class="alert info">${esc(n)}</div>`).join("")}
  </div>
  <div class="card"><h3>Ask for a specific course</h3>
    <form id="pinForm" class="row" style="align-items:center"><select id="pinCode">${state.kb.courses.map((c) => `<option value="${esc(c.code)}">${esc(c.code)} - ${esc(c.title)}</option>`).join("")}</select>
    <button class="btn small">Add to my plan</button></form>
    <p class="small muted">The buddy checks prerequisites, offerings and credit limits and tells you if it isn't possible, with the best valid option.</p></div>
  ${p.semesters.map((s) => `<div class="card sem"><h3>Semester ${s.semester} <span class="muted small">${esc(s.season)} - ${s.total_credits}/${s.credit_limit} credits</span></h3>
    ${s.courses.map((c) => `<div class="course"><div class="code">${esc(c.code || "-")}</div>
       <div><div>${esc(c.title)} <span class="badge ${slotBadge[c.slot] || ""}">${esc(c.slot.replace("_", " "))}</span> <span class="small muted">${c.credits} cr${c.mode === "online" ? " - online" : ""}</span></div>
       <div class="why">Why: ${esc(c.reason)}</div></div>
       <div>${c.code && !["core", "backlog"].includes(c.slot) ? `<button class="btn small danger" data-reject="${esc(c.code)}" title="Remove this course from my plan">Not for me</button>` : ""}</div></div>`).join("")}
  </div>`).join("")}
  <div class="card"><h3>Milestones beyond coursework</h3><div class="timeline">
    ${p.milestones.map((m) => `<div class="tl"><div class="badge brand">Sem ${m.semester}${m.week ? " wk " + m.week : ""}</div><div>${esc(m.title)} <span class="small muted">${esc(m.kind)}${m.status !== "planned" ? " - " + esc(m.status) : ""}</span></div></div>`).join("")}
  </div></div>
  ${(p.minor) ? `<div class="card"><h3>${esc(p.minor.name)}</h3><p>${esc(p.minor.reason)}</p></div>` : ""}
  <div class="card"><h3>Was this plan useful?</h3><div class="stars" id="stars">${[1, 2, 3, 4, 5].map((i) => `<button data-r="${i}" aria-label="${i} stars">&#9733;</button>`).join("")}</div>
    <input id="fbComment" placeholder="Optional comment" style="width:100%;margin-top:6px"></div>`;
  $("#toggleChecks").onclick = () => { $("#checks").hidden = !$("#checks").hidden; };
  $$("[data-reject]", el).forEach((b) => (b.onclick = () => override({ type: "reject_course", course: b.dataset.reject })));
  $("#pinForm").onsubmit = (e) => { e.preventDefault(); override({ type: "pin_course", course: $("#pinCode").value }); };
  $$("#stars button").forEach((b) => (b.onclick = async () => {
    await api(`/api/students/${state.sid}/feedback`, { method: "POST", body: { rating: +b.dataset.r, target: "plan v" + d.plan_version, comment: $("#fbComment").value } });
    toast("Thanks - feedback recorded");
  }));
}

async function override(action) {
  try {
    const r = await api(`/api/students/${state.sid}/override`, { method: "POST", body: action });
    await refresh();
    const inf = (r.infeasible || []).map((i) => i.message).join(" ");
    toast(inf || (r.applied.join("; ") + ` - plan v${r.plan_version}`));
  } catch (e) { toast(e.message); }
}

/* ------------------------------------------------------------ learn & practise */
function renderLearn() {
  const d = state.dash, t = d.plan.learning_track;
  const el = $("#tab-learn");
  if (!d.plan.goal) { el.innerHTML = `<div class="card"><p>Set a goal first.</p></div>`; return; }
  const done = new Set(d.modules_done);
  const wk = t.weeks.find((w) => w.week === state.week) || t.weeks[0];
  el.innerHTML = `
  <div class="card"><h2>Semester ${t.semester} learning track</h2>
    <p class="small muted">${t.hours_per_week} h/week (exam weeks halved), ${t.total_hours} h scheduled${t.pace_factor !== 1 ? `, time scaled x${t.pace_factor} to your pace` : ""}. Active practice comes first; lessons you already know are skipped.</p>
    <div class="weeks">${t.weeks.map((w) => `<button data-week="${w.week}" class="${w.week === wk.week ? "active" : ""}" title="${w.hours}/${w.capacity} h">W${w.week}${w.items.length ? "" : " -"}</button>`).join("")}</div>
    <h3>Week ${wk.week} <span class="small muted">${wk.hours}/${wk.capacity} h</span></h3>
    ${wk.items.length ? wk.items.map((it) => {
      const isDone = it.module && done.has(it.module);
      const typeBadge = { lesson: "info", practice: "ok", assessment: "brand", remedial: "warn" }[it.type] || "";
      return `<div class="item ${isDone ? "done" : ""}"><span class="badge ${typeBadge}">${esc(it.type)}</span>
        <div><strong>${esc(it.title)}</strong> <span class="small muted">${it.hours} h - ${esc(skillName(it.skill))}</span>
        ${it.resource ? `<div class="small"><a href="${esc(it.resource.url)}" target="_blank" rel="noopener">${esc(it.resource.title)}</a> <span class="muted">(${esc(it.resource.provider)}, ${esc(it.resource.format)}, ${esc(it.resource.license)})</span></div>` : ""}
        <div class="why">${esc(it.why || "")}</div></div>
        <div>${it.type === "assessment" ? `<button class="btn small" data-checkpoint="${esc(it.skill)}">Take quiz</button>`
          : it.module ? (isDone ? '<span class="badge ok">done</span>' : `<button class="btn small ghost" data-done="${esc(it.module)}">Mark done</button>`) : ""}
          <button class="btn small ghost" data-practice="${esc(it.skill)}">Practise</button></div></div>`;
    }).join("") : "<p class='muted'>Nothing scheduled this week (buffer).</p>"}
  </div>
  <div class="card" id="practiceCard"><h3>Practice</h3><p class="muted small">Pick "Practise" on any item. Questions adapt to your level; attempts and time are used to adapt your plan.</p><div id="practiceBox"></div></div>
  ${t.skipped.length ? `<div class="card"><h3>Skipped because you already know it (${t.skipped.length})</h3><ul class="small">${t.skipped.slice(0, 12).map((s) => `<li>${esc(s.title)} - <span class="muted">${esc(s.why)}</span></li>`).join("")}</ul></div>` : ""}
  ${t.deferred.length ? `<div class="card"><h3>Moved to next semester to respect your ${t.hours_per_week} h/week (${t.deferred.length})</h3><ul class="small">${t.deferred.slice(0, 12).map((s) => `<li>${esc(s.title)} (${s.hours} h)</li>`).join("")}</ul><p class="small muted">Add hours in chat ("I can do 10 hours per week") to pull these in.</p></div>` : ""}`;
  $$("[data-week]", el).forEach((b) => (b.onclick = () => { state.week = +b.dataset.week; renderLearn(); }));
  $$("[data-done]", el).forEach((b) => (b.onclick = async () => { await api(`/api/students/${state.sid}/modules/${b.dataset.done}/complete`, { method: "POST" }); await refresh(); toast("Module completed - plan updated"); }));
  $$("[data-practice]", el).forEach((b) => (b.onclick = () => startPractice(b.dataset.practice)));
  $$("[data-checkpoint]", el).forEach((b) => (b.onclick = () => { showTab("assess"); startQuiz("checkpoint", b.dataset.checkpoint); }));
}

async function startPractice(skill) {
  try {
    const q = await api(`/api/students/${state.sid}/practice?skill=${encodeURIComponent(skill)}`);
    state.practice = { q, attempts: 1, t0: Date.now() };
    renderPracticeQ();
    $("#practiceCard").scrollIntoView({ behavior: "smooth" });
  } catch (e) { toast(e.message); }
}
function renderPracticeQ(feedback) {
  const { q } = state.practice;
  $("#practiceBox").innerHTML = `<div class="small muted">${esc(skillName(q.skill))} - difficulty ${q.difficulty}</div><div class="q">${esc(q.prompt)}</div>
    <div class="opts">${q.options.map((o) => `<button data-opt="${esc(o)}">${esc(o)}</button>`).join("")}</div><div id="pfb">${feedback || ""}</div>`;
  $$("#practiceBox [data-opt]").forEach((b) => (b.onclick = () => answerPractice(b)));
}
async function answerPractice(btn) {
  const p = state.practice;
  const r = await api(`/api/students/${state.sid}/practice/answer`, { method: "POST",
    body: { question_id: p.q.id, choice: btn.dataset.opt, attempts: p.attempts, seconds: (Date.now() - p.t0) / 1000 } });
  $$("#practiceBox [data-opt]").forEach((b) => { if (b.dataset.opt === r.correct_answer) b.classList.add("right"); });
  if (!r.correct) btn.classList.add("wrong");
  $("#pfb").innerHTML = `<div class="alert ${r.correct ? "ok" : "bad"}">${r.correct ? "Correct!" : "Not quite."} ${esc(r.explanation)}
    <div class="small">Mastery now ${pct(r.mastery)} (confidence ${pct(r.confidence)})</div></div>
    <button class="btn small" id="nextP">Next question</button>`;
  $("#nextP").onclick = () => startPractice(p.q.skill);
  const keepWeek = state.week; await refresh(); state.week = keepWeek;
}

/* ------------------------------------------------------------ assess */
function renderAssess() {
  const el = $("#tab-assess");
  const d = state.dash;
  el.innerHTML = `
  <div class="card"><h2>Assessments</h2>
    <p>Short and adaptive: each skill starts at medium difficulty and moves up or down with your answers. Only skills without recent tested evidence are included.</p>
    <div class="row"><button class="btn" id="startDiag">Start adaptive diagnostic (max 12 questions)</button>
    ${d.plan.goal ? `<button class="btn ghost" id="startMock">Timed mock test (12 min)</button>` : ""}</div>
    <div id="quizBox" style="margin-top:14px"></div></div>
  <div class="card"><h3>Record a project, mock interview or mentor review</h3>
    <form id="evForm" class="grid2">
      <label>Skill<select name="skill_id">${state.kb.skills.map((s) => `<option value="${esc(s.id)}">${esc(s.name)}</option>`).join("")}</select></label>
      <label>Type<select name="source"><option value="project">Project checkpoint</option><option value="mock">Mock interview / timed test</option><option value="assessment">External assessment</option></select></label>
      <label>Score (0-100)<input name="score" type="number" min="0" max="100" value="70"></label>
      <label>Details<input name="detail" placeholder="e.g. analytics project reviewed by mentor"></label>
      <div><button class="btn small">Save evidence</button></div></form>
    <p class="small muted">Projects and mocks are strong evidence for goal-level mastery (e.g. placement readiness), beyond course grades.</p></div>`;
  $("#startDiag").onclick = () => startQuiz("diagnostic");
  if ($("#startMock")) $("#startMock").onclick = () => startQuiz("mock");
  $("#evForm").onsubmit = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const r = await api(`/api/students/${state.sid}/evidence`, { method: "POST",
      body: { skill_id: f.get("skill_id"), source: f.get("source"), score: (+f.get("score")) / 100, detail: f.get("detail") || "" } });
    await refresh(); toast(`Evidence saved - plan v${r.plan_version}`);
  };
  if (state.quiz) renderQuizQ();
}
async function startQuiz(mode, skill) {
  try {
    const r = await api(`/api/students/${state.sid}/assessments`, { method: "POST", body: { mode, skill } });
    state.quiz = { ...r, n: 0, t0: Date.now(), started: Date.now() };
    renderQuizQ();
  } catch (e) { toast(e.message); }
}
function renderQuizQ(fb) {
  const z = state.quiz, box = $("#quizBox");
  if (!box || !z) return;
  if (!z.question) return;
  const label = { diagnostic: "Adaptive diagnostic", checkpoint: "Checkpoint quiz", mock: "Timed mock" }[z.mode];
  const left = z.time_limit_min ? Math.max(0, z.time_limit_min * 60 - (Date.now() - z.started) / 1000) : null;
  box.innerHTML = `<div class="small muted">${label} - question ${z.n + 1} of ${z.total_questions}${left != null ? ` - ${Math.floor(left / 60)}:${String(Math.floor(left % 60)).padStart(2, "0")} left` : ""}</div>
    <div class="progress"><div style="width:${(z.n / z.total_questions) * 100}%"></div></div>
    <div class="small"><span class="badge">${esc(skillName(z.question.skill))}</span> <span class="badge">${["", "easy", "medium", "hard"][z.question.difficulty]}</span></div>
    <div class="q">${esc(z.question.prompt)}</div>
    <div class="opts">${z.question.options.map((o) => `<button data-qopt="${esc(o)}">${esc(o)}</button>`).join("")}</div>${fb || ""}`;
  $$("[data-qopt]", box).forEach((b) => (b.onclick = () => answerQuiz(b.dataset.qopt)));
}
async function answerQuiz(choice) {
  const z = state.quiz;
  $$("[data-qopt]").forEach((b) => (b.disabled = true));
  const r = await api(`/api/assessments/${z.session_id}/answer`, { method: "POST", body: { question_id: z.question.id, choice, seconds: (Date.now() - z.t0) / 1000 } });
  z.n += 1; z.t0 = Date.now();
  if (r.finished) {
    state.quiz = null;
    await refresh();
    showTab("assess");
    $("#quizBox").innerHTML = `<div class="alert ok"><strong>Done!</strong> Your plan was updated (v${r.plan_version}).</div>
      <h3>Results</h3>${r.summary.map((s) => `<div class="skill"><div>${esc(s.name)}</div><div class="bar"><div class="fill" style="width:${s.mastery * 100}%"></div></div><div>${pct(s.mastery)} ${s.status ? `<span class="badge ${(STATUS[s.status] || [])[1] || ""}">${esc((STATUS[s.status] || [s.status])[0])}</span>` : ""}</div></div>`).join("")}
      ${r.plan_diff?.changes ? `<h3 style="margin-top:12px">How your plan changed</h3><ul class="diff">${r.plan_diff.changes.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>` : ""}`;
    return;
  }
  z.question = r.next_question;
  renderQuizQ(`<div class="alert ${r.correct ? "ok" : "bad"} small">${r.correct ? "Correct." : "Answer: " + esc(r.correct_answer) + "."} ${esc(r.explanation)}</div>`);
}

/* ------------------------------------------------------------ adapt (simulation) */
function renderAdapt() {
  const el = $("#tab-adapt");
  const gaps = state.dash.diagnosis.gaps;
  if (!gaps.length) { el.innerHTML = `<div class="card"><p>Set a goal first.</p></div>`; return; }
  el.innerHTML = `<div class="card"><h2>See how your plan adapts</h2>
    <p>Simulate a mid-semester quiz result and compare the plan before and after. Nothing is saved.</p>
    <div class="row" style="align-items:center"><select id="simSkill">${gaps.map((g) => `<option value="${esc(g.skill)}">${esc(g.name)}</option>`).join("")}</select>
    <button class="btn" data-sim="strong">Strong quiz (92%)</button><button class="btn ghost" data-sim="weak">Weak quiz (22%, 3 attempts)</button></div></div>
    <div id="simOut"></div>`;
  $$("[data-sim]", el).forEach((b) => (b.onclick = () => simulate(b.dataset.sim)));
}
function planBrief(p) {
  const s = p.semesters[0], t = p.learning_track;
  const items = t.weeks.flatMap((w) => w.items).filter((i) => !/\(part [2-9]/.test(i.title));
  return `<div><strong>Semester ${s.semester} courses</strong><ul class="small">${s.courses.map((c) => `<li><span class="code">${esc(c.code || "-")}</span> ${esc(c.title)}</li>`).join("")}</ul>
    <strong>Learning track</strong> <span class="small muted">(${t.total_hours} h, ${t.deferred.length} deferred)</span>
    <ul class="small">${items.slice(0, 10).map((i) => `<li><span class="badge">${esc(i.type)}</span> ${esc(i.title)}</li>`).join("")}${items.length > 10 ? `<li class="muted">+${items.length - 10} more</li>` : ""}</ul>
    <div class="small">Projected readiness: <strong>${pct(p.readiness_projected)}</strong></div></div>`;
}
async function simulate(preset) {
  const skill = $("#simSkill").value;
  $("#simOut").innerHTML = `<div class="card"><span class="spinner"></span> Simulating...</div>`;
  const r = await api(`/api/students/${state.sid}/simulate`, { method: "POST", body: { preset, skill } });
  $("#simOut").innerHTML = `<div class="card"><h3>After a ${preset} quiz in ${esc(skillName(skill))}</h3>
    <ul class="diff">${r.diff.changes.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>
    <div class="compare"><div class="card"><h3>Before</h3>${planBrief(r.before.plan)}</div><div class="card"><h3>After</h3>${planBrief(r.after.plan)}</div></div>
    <p class="small muted">Both plans pass validation: ${r.before.validation.passed && r.after.validation.passed ? "yes" : "no"}.</p></div>`;
}

/* ------------------------------------------------------------ history */
async function renderHistory() {
  const el = $("#tab-history");
  el.innerHTML = `<div class="card"><span class="spinner"></span></div>`;
  const [plans, mem] = await Promise.all([api(`/api/students/${state.sid}/plans`), api(`/api/students/${state.sid}/memory`)]);
  el.innerHTML = `<div class="card"><h2>Plan versions</h2>${plans.map((p) => `<div class="item"><span class="badge brand">v${p.version}</span>
    <div><strong>${esc(p.reason)}</strong> <span class="small muted">${new Date(p.created_at).toLocaleString()}</span>
    <ul class="small diff">${(p.diff?.changes || []).map((c) => `<li>${esc(c)}</li>`).join("")}</ul></div>
    <span class="badge ${p.passed ? "ok" : "bad"}">${p.passed ? "valid" : "invalid"}</span></div>`).join("")}</div>
    <div class="card"><h2>What the buddy remembers</h2><p class="small muted">Long-term memory survives across sessions so you never have to repeat yourself.</p>
    ${mem.map((m) => `<div class="item"><span class="badge">${esc(m.kind)}</span><div class="small">${esc(m.content)}</div><span class="small muted">${new Date(m.at).toLocaleDateString()}</span></div>`).join("") || "<p class='muted'>Nothing yet.</p>"}</div>`;
}

/* ------------------------------------------------------------ chat */
function addMsg(role, text, meta) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.innerHTML = esc(text) + (meta ? `<div class="meta">${meta}</div>` : "");
  $("#chatLog").appendChild(div);
  $("#chatLog").scrollTop = 1e9;
  return div;
}
async function loadChat() {
  $("#chatLog").innerHTML = "";
  if (state.session) {
    const msgs = await api(`/api/students/${state.sid}/chat?session_id=${state.session}`);
    msgs.forEach((m) => addMsg(m.role, m.content));
  }
  if (!$("#chatLog").children.length) greet();
  const chips = ["How am I doing?", "Why these courses?", "What should I do this week?", "What changed in my plan?", "I can only study 5 hours per week"];
  $("#chatChips").innerHTML = chips.map((c) => `<button>${esc(c)}</button>`).join("");
  $$("#chatChips button").forEach((b) => (b.onclick = () => sendChat(b.textContent)));
}
function greet() {
  const d = state.dash;
  addMsg("assistant", d.diagnosis.goal_is_vague
    ? `Hi ${d.student.name}! Before I plan anything: what would you like to be doing after graduation? A job (software, data, core), higher studies, civil services, a startup...?`
    : `Hi ${d.student.name}! I remember your goal (${d.diagnosis.goal.name}) and your plan v${d.plan_version}. Ask me why something is in your plan, tell me what you'd like to change, or ask any study question.`);
}
async function sendChat(text) {
  text = (text || "").trim();
  if (!text) return;
  $("#chatInput").value = "";
  addMsg("user", text);
  const wait = addMsg("assistant", "...");
  try {
    const r = await api(`/api/students/${state.sid}/chat`, { method: "POST", body: { message: text, session_id: state.session } });
    state.session = r.session_id; localSet("chatSession", r.session_id);
    wait.remove();
    const meta = [r.applied.length ? "Applied: " + esc(r.applied.join("; ")) : "", r.applied.length ? `plan v${r.plan_version}` : ""].filter(Boolean).join(" - ");
    addMsg("assistant", r.reply, meta);
    if (r.applied.length) await refresh();
  } catch (e) { wait.textContent = "Sorry, something went wrong: " + e.message; }
}

/* ------------------------------------------------------------ onboarding */
function setupOnboarding() {
  $("#obProgramme").innerHTML = state.kb.programmes.map((p) => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join("");
  $("#obGoal").innerHTML = `<option value="">- not sure yet -</option>` + state.kb.goals.map((g) => `<option value="${esc(g.id)}">${esc(g.name)}</option>`).join("");
  const rate = ["prog_fund", "dsa", "prob_stats", "data_analysis", "economics", "tech_writing"];
  $("#obRatings").innerHTML = rate.map((s) => `<label>${esc(skillName(s))}<input type="number" min="0" max="100" name="rate_${s}" placeholder="-"></label>`).join("");
  $("#obGoalText").oninput = (e) => {
    const t = e.target.value.toLowerCase();
    const hits = state.kb.goals.filter((g) => t && (g.name.toLowerCase().split(/\W+/).some((w) => w.length > 3 && t.includes(w))));
    $("#obGoalMatch").textContent = hits.length ? "Sounds like: " + hits.map((g) => g.name).join(" / ") : "";
  };
  $("#onboardForm").onsubmit = async (e) => {
    if (e.submitter?.value !== "ok") return;
    e.preventDefault();
    const f = new FormData(e.target);
    const ratings = {};
    rate.forEach((s) => { const v = f.get("rate_" + s); if (v !== "" && v != null) ratings[s] = +v / 100; });
    try {
      const r = await api("/api/students", { method: "POST", body: {
        name: f.get("name"), programme: f.get("programme"), year: +f.get("year"), cgpa: +f.get("cgpa"),
        goal_text: f.get("goal_text") || "", goal_id: f.get("goal_id") || "", interests: (f.get("interests") || "").split(",").map((x) => x.trim()).filter(Boolean),
        hours_per_week: +f.get("hours") || 6, max_credits: f.get("max_credits") ? +f.get("max_credits") : null,
        formats: f.getAll("fmt"), pace: f.get("pace"), self_ratings: ratings } });
      $("#onboard").close();
      await boot();
      $("#studentSelect").value = r.id;
      await selectStudent(r.id);
      showTab(r.goal_id ? "assess" : "overview");
      toast(r.goal_id ? "Profile created - take the short diagnostic to calibrate your plan" : "Profile created - let's clarify your goal");
    } catch (err) { toast(err.message); }
  };
}
function openOnboarding() { $("#onboardForm").reset(); $("#onboard").showModal(); }

boot().catch((e) => { document.body.insertAdjacentHTML("beforeend", `<p style="padding:20px">Failed to load: ${esc(e.message)}</p>`); });
