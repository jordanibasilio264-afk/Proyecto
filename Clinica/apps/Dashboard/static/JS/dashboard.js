const data = JSON.parse(document.getElementById("chart-data").textContent);

new Chart(document.getElementById("chartConsultas"), {
  type: "bar",
  data: {
    labels: data.meses,
    datasets: [{ label: "Consultas", data: data.consultas }],
  },
  options: { responsive: true, maintainAspectRatio: false,
             scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
});

new Chart(document.getElementById("chartEstadoCitas"), {
  type: "doughnut",
  data: {
    labels: data.estados.etiquetas,
    datasets: [{ data: data.estados.valores }],
  },
  options: { responsive: true, maintainAspectRatio: false },
});