/* RF-08: Consultas médicas y documentos asociados a pacientes.
   Los datos se guardan en la base de datos vía las vistas de apps/Documentos/views.py. */

const $ = s => document.querySelector(s);
const getCSRF = () => document.querySelector("[name=csrfmiddlewaretoken]")?.value;

const wrap = $(".wrap");
const URLS = {
  consultas: wrap.dataset.urlConsultas,
  documentos: wrap.dataset.urlDocumentos,
  desactivar: wrap.dataset.urlDesactivar,
};
const withId = (tpl, id) => tpl.replace("/0/", `/${id}/`);

let consultas = [];   // del paciente seleccionado
let docs = [];
let pid = "";
let consultaPreferida = null;   // consulta recién creada: se preselecciona en Documentos

const esc = t => String(t ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = d => new Date(d).toLocaleString("es-DO", { dateStyle: "medium", timeStyle: "short" });
const size = b => b < 1048576 ? (b / 1024).toFixed(1) + " KB" : (b / 1048576).toFixed(1) + " MB";

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 3200);
}

/* fetch con CSRF; lanza Error con el mensaje del servidor */
async function api(url, opts = {}) {
  const res = await fetch(url, {
    credentials: "same-origin",
    ...opts,
    headers: { "X-CSRFToken": getCSRF(), ...(opts.headers || {}) },
  });
  let data = {};
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) {
    const msg = Object.values(data.errores || {}).flat().join(" ") || `No se pudo completar la operación (error ${res.status}).`;
    throw new Error(msg);
  }
  return data;
}

async function cargar() {
  if (!pid) { consultas = []; docs = []; return render(); }
  try {
    const [c, d] = await Promise.all([
      api(withId(URLS.consultas, pid)),
      api(withId(URLS.documentos, pid)),
    ]);
    consultas = c.consultas; docs = d.documentos;
  } catch (e) { consultas = []; docs = []; toast(e.message); }
  render();
}

/* ---------- Paciente ---------- */
function seleccionarPaciente() {
  const texto = $("#pacienteInput").value.trim();
  const opt = [...$("#listaPacientes").options].find(o => o.value === texto);
  const nuevo = opt ? opt.dataset.id : "";
  if (nuevo === pid) return;          // evita recargar mientras escribes
  pid = nuevo;
  $("#paciente_id").value = pid;
  $("#pInfo").hidden = !pid;
  if (pid) {
    $("#iSangre").textContent = opt.dataset.sangre || "—";
    $("#iEdad").textContent = (opt.dataset.edad || "—") + " años";
  }
  $("#fsConsulta").disabled = $("#fsDoc").disabled = !pid;
  $("#filtro").value = "";
  consultas = []; docs = []; render();
  cargar();
}
$("#pacienteInput").addEventListener("input", seleccionarPaciente);

/* ---------- Médico (solo ADMIN) ---------- */
function seleccionarMedico() {
  const input = $("#consultaMedico"), hidden = $("#consultaMedicoPk");
  if (!input || !hidden) return;
  const opt = [...$("#listaMedicos").options].find(o => o.value === input.value.trim());
  hidden.value = opt ? opt.dataset.pk : "";
}
$("#consultaMedico")?.addEventListener("input", seleccionarMedico);

/* ---------- Pestañas ---------- */
document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.toggle("active", x === t));
  document.querySelectorAll(".panel").forEach(p => p.classList.toggle("active", p.id === t.dataset.tab));
});

/* ---------- Consultas ---------- */
function fechaLocal() {
  return new Date(Date.now() - new Date().getTimezoneOffset() * 6e4).toISOString().slice(0, 16);
}
$("#cFecha").value = fechaLocal();

$("#formConsulta").onsubmit = async ev => {
  ev.preventDefault();
  if (!pid) return;
  const v = id => $(id)?.value.trim() ?? "";
  const form = ev.target, btn = form.querySelector("button");

  const payload = {
    fecha: v("#cFecha"), motivo: v("#cMotivo"), presion: v("#vPA"),
    fc: v("#vFC"), temp: v("#vTemp"), fr: v("#vFR"), sat: v("#vSat"), peso: v("#vPeso"),
    diagnostico: v("#cDiag"), tratamiento: v("#cTrat"), observaciones: v("#cObs"),
    enfermedad_actual: v("#cEnf"),
    requiere_seguimiento: $("#cSeg")?.checked ?? false,
    fecha_seguimiento: $("#cFechaSeg")?.value ?? "",
  };

  // Solo existe para el ADMIN
  if ($("#consultaMedico")) {
    seleccionarMedico();   // por si el navegador autocompletó sin disparar "input"
    const medicoPk = $("#consultaMedicoPk").value;
    if (!medicoPk) { toast("Selecciona un médico de la lista."); return; }
    payload.medico_id = medicoPk;
  }

  btn.disabled = true;
  try {
    const r = await api(withId(URLS.consultas, pid), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    form.reset(); $("#cFecha").value = fechaLocal();
    consultaPreferida = r.consulta.id;
    await cargar(); toast("Consulta guardada");
  } catch (e) { toast(e.message); }
  finally { btn.disabled = false; }
};

/* Seguimiento: la fecha solo se habilita si se marca el checkbox */
function syncSeguimiento() {
  const seg = $("#cSeg"), fecha = $("#cFechaSeg");
  if (!seg || !fecha) return;
  fecha.disabled = !seg.checked;
  if (!seg.checked) fecha.value = "";
}
$("#cSeg")?.addEventListener("change", syncSeguimiento);
$("#formConsulta").addEventListener("reset", () => setTimeout(syncSeguimiento));
syncSeguimiento();

$("#filtro").oninput = renderConsultas;

function signos(c) {
  const s = c.vitales;
  return {
    "Presión": s.pa, "Pulso": s.fc && s.fc + " lpm", "Temp.": s.temp && s.temp + " °C",
    "Resp.": s.fr && s.fr + " rpm", "SpO₂": s.sat && s.sat + "%", "Peso": s.peso && s.peso + " kg",
  };
}

function renderConsultas() {
  const q = $("#filtro").value.trim().toLowerCase();
  const lista = pid ? consultas.filter(c => (c.motivo + c.diagnostico).toLowerCase().includes(q)) : [];
  $("#timeline").innerHTML = lista.length ? lista.map(c => {
    const chips = Object.entries(signos(c)).filter(([, v]) => v).map(([k, v]) => `<span class="chip">${k}: ${esc(v)}</span>`).join("");
    return `<article class="entry">
      <div class="entry-head"><span>${esc(c.motivo)}</span><small>${fmt(c.fecha)}</small></div>
      ${chips ? `<div class="chips">${chips}</div>` : ""}
      ${c.enfermedad_actual ? `<p><b>Enfermedad actual:</b> ${esc(c.enfermedad_actual)}</p>` : ""}
      <p><b>Diagnóstico:</b> ${esc(c.diagnostico)}</p>
      ${c.tratamiento ? `<p><b>Tratamiento:</b> ${esc(c.tratamiento)}</p>` : ""}
      ${c.observaciones ? `<p><b>Observaciones:</b> ${esc(c.observaciones)}</p>` : ""}
      ${c.requiere_seguimiento ? `<p><b>Seguimiento:</b> ${c.fecha_seguimiento ? new Date(c.fecha_seguimiento + "T00:00").toLocaleDateString("es-DO", { dateStyle: "medium" }) : "pendiente"}</p>` : ""}
      <small style="color:var(--muted)">Dr(a). ${esc(c.medico)}</small>
    </article>`;
  }).join("") : `<p class="empty">${!pid ? "Seleccione un paciente para ver su historial."
      : q ? "Ninguna consulta coincide con el filtro." : "Este paciente aún no tiene consultas. Registre la primera en el formulario."}</p>`;
}

/* ---------- Documentos ---------- */
$("#formDoc").onsubmit = async ev => {
  ev.preventDefault();
  const f = $("#dFile").files[0]; if (!pid || !f) return;
  const form = ev.target, btn = form.querySelector("button");
  const fd = new FormData();
  fd.append("archivo", f);
  fd.append("tipo", $("#dTipo").value);
  fd.append("descripcion", $("#dDesc").value.trim());
  fd.append("consulta", $("#dConsulta")?.value ?? "");
  btn.disabled = true;
  try {
    await api(withId(URLS.documentos, pid), { method: "POST", body: fd });
    form.reset(); await cargar(); toast("Documento subido");
  } catch (e) { toast(e.message); }
  finally { btn.disabled = false; }
};

const consultaDe = d => consultas.find(c => c.id === d.consulta_id);

/* Select "Consulta asociada": por defecto la más reciente del paciente */
function renderSelectConsultas() {
  const sel = $("#dConsulta");
  if (!sel) return;
  const actual = consultaPreferida ?? sel.value;
  consultaPreferida = null;
  const lista = pid ? consultas : [];
  sel.innerHTML = '<option value="">Sin consulta asociada</option>' +
    lista.map(c => `<option value="${c.id}">${fmt(c.fecha)} · ${esc(c.motivo)}</option>`).join("");
  const existe = lista.some(c => String(c.id) === String(actual));
  sel.value = existe ? String(actual) : (lista[0] ? String(lista[0].id) : "");
}

function renderDocs() {
  const lista = pid ? docs : [];
  $("#tbDocs").innerHTML = lista.length ? lista.map(d => `
    <tr>
      <td><b>${esc(d.titulo)}</b><br><small style="color:var(--muted)">${size(d.tam)}${d.descripcion ? " · " + esc(d.descripcion) : ""}${consultaDe(d) ? " · Consulta: " + esc(consultaDe(d).motivo) : ""}</small></td>
      <td>${esc(d.tipo)}</td><td>${fmt(d.fecha)}</td>
      <td class="act">
        <a class="btn btn-ghost btn-sm" href="${esc(d.url)}" target="_blank" rel="noopener">Ver</a>
        <button class="btn btn-danger btn-sm" data-del="${d.id}">Eliminar</button>
      </td>
    </tr>`).join("")
    : `<tr><td colspan="4" class="empty">${pid ? "Este paciente no tiene documentos. Suba el primero en el formulario." : "Seleccione un paciente para ver sus documentos."}</td></tr>`;
}

$("#tbDocs").onclick = async ev => {
  const b = ev.target.closest("[data-del]"); if (!b) return;
  const d = docs.find(x => x.id == b.dataset.del);
  if (!d || !confirm(`¿Eliminar "${d.titulo}"?`)) return;
  try {
    await api(withId(URLS.desactivar, d.id), { method: "POST" });
    await cargar(); toast("Documento eliminado");
  } catch (e) { toast(e.message); }
};

/* ---------- Render general ---------- */
function render() {
  $("#nCons").textContent = pid ? consultas.length : 0;
  $("#nDocs").textContent = pid ? docs.length : 0;
  renderSelectConsultas(); renderConsultas(); renderDocs();
}
render();