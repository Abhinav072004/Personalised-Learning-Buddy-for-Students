/* Admin data-control page: browse and edit any table through the admin API. */
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const PK = { students: "id", evidence: "id", courses: "code", prerequisites: "id", course_skills: "id", skills: "id", modules: "id",
  resources: "id", questions: "id", goals: "id", minors: "id", rules: "key", programmes: "id", plans: "id", memories: "id" };
let rows = [], editing = null;

function toast(m) { const t = $("#toast"); t.textContent = m; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 3500); }
async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).detail || m; } catch { } throw new Error(typeof m === "string" ? m : JSON.stringify(m)); }
  return r.json();
}
const cell = (v) => { const s = typeof v === "object" && v !== null ? JSON.stringify(v) : String(v ?? ""); return esc(s.length > 90 ? s.slice(0, 90) + "..." : s); };

async function load() {
  const t = $("#table").value;
  $("#status").textContent = "loading...";
  rows = await api(`/api/admin/tables/${t}`);
  render();
}
function render() {
  const f = $("#filter").value.toLowerCase();
  const list = rows.filter((r) => !f || JSON.stringify(r).toLowerCase().includes(f));
  const cols = list.length ? Object.keys(list[0]) : [];
  $("#grid").innerHTML = `<tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}<th></th></tr>` +
    list.slice(0, 300).map((r, i) => `<tr>${cols.map((c) => `<td>${cell(r[c])}</td>`).join("")}<td><button class="btn small ghost" data-i="${rows.indexOf(r)}">Edit</button></td></tr>`).join("");
  document.querySelectorAll("[data-i]").forEach((b) => (b.onclick = () => openEdit(rows[+b.dataset.i])));
  $("#status").textContent = `${list.length} rows${list.length > 300 ? " (first 300 shown)" : ""}`;
}
function openEdit(row) {
  editing = row;
  $("#editTitle").textContent = row ? `Edit ${$("#table").value} / ${row[PK[$("#table").value]]}` : `New row in ${$("#table").value}`;
  $("#editJson").value = JSON.stringify(row || {}, null, 2);
  $("#delBtn").style.display = row ? "" : "none";
  $("#editDlg").showModal();
}
$("#editForm").onsubmit = async (e) => {
  const action = e.submitter?.value;
  if (action === "cancel") return;
  e.preventDefault();
  const t = $("#table").value, pk = PK[t];
  try {
    let r;
    if (action === "del") {
      if (!confirm("Delete this row?")) return;
      r = await api(`/api/admin/tables/${t}/${encodeURIComponent(editing[pk])}`, { method: "DELETE" });
    } else {
      const val = JSON.parse($("#editJson").value);
      if (editing) {
        const changed = {};
        for (const k of Object.keys(val)) if (k !== pk && JSON.stringify(val[k]) !== JSON.stringify(editing[k])) changed[k] = val[k];
        if (!Object.keys(changed).length) { $("#editDlg").close(); return; }
        r = await api(`/api/admin/tables/${t}/${encodeURIComponent(editing[pk])}`, { method: "PUT", body: changed });
      } else {
        r = await api(`/api/admin/tables/${t}`, { method: "POST", body: val });
      }
    }
    $("#editDlg").close();
    toast("Saved" + (r.replanned != null ? ` - ${r.replanned} plans re-generated` : r.plan_version ? ` - plan v${r.plan_version}` : ""));
    load();
  } catch (err) { toast("Error: " + err.message); }
};
$("#newRow").onclick = () => openEdit(null);
$("#filter").oninput = render;
$("#table").onchange = load;
$("#resetBtn").onclick = async () => {
  if (!confirm("Restore the original seed data? All plans, chats and evidence added since will be lost.")) return;
  const r = await api("/api/admin/reset", { method: "POST" });
  toast(r.message); load();
};
$("#adminerLink").href = `${location.protocol}//${location.hostname}:8080/?pgsql=db&username=buddy&db=buddy`;
(async () => {
  const tables = await api("/api/admin/tables");
  $("#table").innerHTML = tables.map((t) => `<option ${t === "students" ? "selected" : ""}>${esc(t)}</option>`).join("");
  load();
})();
