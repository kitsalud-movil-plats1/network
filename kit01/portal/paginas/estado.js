// Estado de los servicios en el menú del portal. Pregunta a /estado cada 30 s, abre
// el apartado si algo falla y escribe solo texto, nunca HTML.
(function () {
  var TEXTOS = {
    verde: "Funciona",
    amarillo: "Funciona con fallas",
    rojo: "No funciona",
    desconocido: "Sin datos"
  };
  var caja = document.getElementById("estado");
  var punto = document.getElementById("estado-punto");
  var resumen = document.getElementById("estado-resumen");
  var lista = document.getElementById("estado-lista");
  var aviso = document.getElementById("estado-aviso");

  function pintar(nodo, estado) {
    nodo.className = "punto " + estado;
  }

  function mostrar(servicios) {
    var estados = servicios.map(function (s) { return s.estado; });
    var malo = estados.indexOf("rojo") >= 0 || estados.indexOf("amarillo") >= 0;
    var general = estados.indexOf("rojo") >= 0 ? "rojo"
      : estados.indexOf("amarillo") >= 0 ? "amarillo"
      : estados.indexOf("desconocido") >= 0 || !estados.length ? "desconocido" : "verde";
    pintar(punto, general);
    resumen.textContent = malo ? "Un servicio tiene problemas"
      : general === "verde" ? "Todos los servicios funcionan" : "No se pudo revisar el estado";
    aviso.hidden = !malo;
    if (malo) { caja.open = true; }
    lista.textContent = "";
    servicios.forEach(function (s) {
      var fila = document.createElement("li");
      var marca = document.createElement("span");
      var nombre = document.createElement("span");
      var texto = document.createElement("span");
      pintar(marca, s.estado);
      nombre.textContent = s.nombre;
      texto.className = "estado-texto";
      texto.textContent = TEXTOS[s.estado] || TEXTOS.desconocido;
      fila.appendChild(marca);
      fila.appendChild(nombre);
      fila.appendChild(texto);
      lista.appendChild(fila);
    });
  }

  function revisar() {
    fetch("/estado", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (d) { mostrar(d.servicios); })
      .catch(function () { mostrar([]); });
  }

  revisar();
  setInterval(revisar, 30000);
})();
