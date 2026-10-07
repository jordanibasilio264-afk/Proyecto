/* RF-08: Consultas médicas y documentos asociados a pacientes.
   Los datos se guardan en memoria (por paciente) para que la pantalla funcione sola.
   Para conectar con Django reemplace los bloques "// DJANGO:" por fetch() a sus vistas,
   enviando el header X-CSRFToken con getCSRF(). */

const $ = s => document.querySelector(s);
const getCSRF = () => document.querySelector("[name=csrfmiddlewaretoken]")?.value;

const datos = {};   // { pacienteId: { consultas: [], docs: [] } }
let pid = "";

const esc = t => String(t ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = d => new Date(d).toLocaleString("es-DO", { dateStyle: "medium", timeStyle: "short" });
const size = b => b < 1048576 ? (b / 1024).toFixed(1) + " KB" : (b / 1048576).toFixed(1) + " MB";
const actual = () => datos[pid] ??= { consultas: [], docs: [] };

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2400);
}

/* ---------- Paciente ---------- */
$("#paciente").onchange = e => {
  pid = e.target.value;
  const opt = e.target.selectedOptions[0];
  $("#pInfo").hidden = !pid;
  if (pid) { $("#iSangre").textContent = opt.dataset.sangre || "—"; $("#iEdad").textContent = (opt.dataset.edad || "—") + " años"; }
  $("#fsConsulta").disabled = $("#fsDoc").disabled = !pid;
  $("#filtro").value = "";
  render();
};

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

$("#formConsulta").onsubmit = ev => {
  ev.preventDefault();
  if (!pid) return;
  const v = id => $(id).value.trim();
  // DJANGO: POST a /pacientes/<pid>/consultas/ con los campos del formulario.
  actual().consultas.unshift({
    id: Date.now(), fecha: v("#cFecha"), motivo: v("#cMotivo"),
    signos: {
      "Presión": v("#vPA"), "Pulso": v("#vFC") && v("#vFC") + " lpm", "Temp.": v("#vTemp") && v("#vTemp") + " °C",
      "Resp.": v("#vFR") && v("#vFR") + " rpm", "SpO₂": v("#vSat") && v("#vSat") + "%", "Peso": v("#vPeso") && v("#vPeso") + " kg"
    },
    diagnostico: v("#cDiag"), tratamiento: v("#cTrat"), observaciones: v("#cObs")
  });
  ev.target.reset(); $("#cFecha").value = fechaLocal();
  render(); toast("Consulta guardada");
};

$("#filtro").oninput = renderConsultas;

function renderConsultas() {
  const q = $("#filtro").value.trim().toLowerCase();
  const lista = pid ? actual().consultas.filter(c => (c.motivo + c.diagnostico).toLowerCase().includes(q)) : [];
  $("#timeline").innerHTML = lista.length ? lista.map(c => {
    const chips = Object.entries(c.signos).filter(([, v]) => v).map(([k, v]) => `<span class="chip">${k}: ${esc(v)}</span>`).join("");
    return `<article class="entry">
      <div class="entry-head"><span>${esc(c.motivo)}</span><small>${fmt(c.fecha)}</small></div>
      ${chips ? `<div class="chips">${chips}</div>` : ""}
      <p><b>Diagnóstico:</b> ${esc(c.diagnostico)}</p>
      ${c.tratamiento ? `<p><b>Tratamiento:</b> ${esc(c.tratamiento)}</p>` : ""}
      ${c.observaciones ? `<p><b>Observaciones:</b> ${esc(c.observaciones)}</p>` : ""}
    </article>`;
  }).join("") : `<p class="empty">${!pid ? "Seleccione un paciente para ver su historial."
      : q ? "Ninguna consulta coincide con el filtro." : "Este paciente aún no tiene consultas. Registre la primera en el formulario."}</p>`;
}

/* ---------- Documentos ---------- */
$("#formDoc").onsubmit = ev => {
  ev.preventDefault();
  const f = $("#dFile").files[0]; if (!pid || !f) return;
  // DJANGO: envíe FormData (archivo, tipo, descripción, paciente=pid) a su vista de subida.
  actual().docs.unshift({
    id: Date.now(), nombre: f.name, tam: f.size, tipo: $("#dTipo").value,
    desc: $("#dDesc").value.trim(), fecha: new Date(), url: URL.createObjectURL(f)
  });
  ev.target.reset(); render(); toast("Documento subido");
};

function renderDocs() {
  const docs = pid ? actual().docs : [];
  $("#tbDocs").innerHTML = docs.length ? docs.map(d => `
    <tr>
      <td><b>${esc(d.nombre)}</b><br><small style="color:var(--muted)">${size(d.tam)}${d.desc ? " · " + esc(d.desc) : ""}</small></td>
      <td>${esc(d.tipo)}</td><td>${fmt(d.fecha)}</td>
      <td class="act">
        <a class="btn btn-ghost btn-sm" href="${d.url}" download="${esc(d.nombre)}">Descargar</a>
        <button class="btn btn-danger btn-sm" data-del="${d.id}">Eliminar</button>
      </td>
    </tr>`).join("")
    : `<tr><td colspan="4" class="empty">${pid ? "Este paciente no tiene documentos. Suba el primero en el formulario." : "Seleccione un paciente para ver sus documentos."}</td></tr>`;
}

$("#tbDocs").onclick = ev => {
  const b = ev.target.closest("[data-del]"); if (!b) return;
  const d = actual().docs.find(x => x.id == b.dataset.del);
  if (!confirm(`¿Eliminar "${d.nombre}"? Esta acción no se puede deshacer.`)) return;
  // DJANGO: POST/DELETE a su vista de eliminación.
  URL.revokeObjectURL(d.url);
  actual().docs = actual().docs.filter(x => x !== d);
  render(); toast("Documento eliminado");
};

/* ---------- Render general ---------- */
function render() {
  $("#nCons").textContent = pid ? actual().consultas.length : 0;
  $("#nDocs").textContent = pid ? actual().docs.length : 0;
  renderConsultas(); renderDocs();
}
render();