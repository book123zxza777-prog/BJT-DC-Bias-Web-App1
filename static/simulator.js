// UI-only progressive enhancement for the Lab 04 simulator.
// No physics or plotting happens here: the server owns ngspice and all data.
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  ready(function () {
    var form = document.querySelector("[data-sim-form]");
    if (!form) {
      return;
    }

    var radios = Array.prototype.slice.call(
      form.querySelectorAll("[data-analysis-radio]")
    );
    var groups = Array.prototype.slice.call(
      form.querySelectorAll("[data-analysis-group]")
    );
    var button = form.querySelector("[data-run-button]");
    var status = form.querySelector("[data-run-status]");
    var defaultButtonText = button ? button.textContent.trim() : "";
    var defaultStatusText = status ? status.textContent.trim() : "";

    function selectedAnalysis() {
      for (var i = 0; i < radios.length; i += 1) {
        if (radios[i].checked) {
          return radios[i].value;
        }
      }
      return "dc";
    }

    function updateGroups() {
      var analysis = selectedAnalysis();
      groups.forEach(function (group) {
        var name = group.getAttribute("data-analysis-group");
        if (name === "load") {
          group.hidden = analysis === "dc";
        } else if (name === "source") {
          group.hidden = analysis !== "tran";
        } else {
          group.hidden = false;
        }
      });

      if (button) {
        var short = analysis === "tran" ? "Transient" : analysis.toUpperCase();
        button.textContent = "Run ngspice — " + short;
      }
      if (status && !status.classList.contains("is-running")) {
        status.classList.remove("is-error");
        status.textContent =
          "พร้อมรันโหมด " +
          (analysis === "tran" ? "Transient" : analysis.toUpperCase()) +
          " — ผลจะมาจาก ngspice จริง";
      }
    }

    radios.forEach(function (radio) {
      radio.addEventListener("change", updateGroups);
    });

    form.addEventListener("submit", function () {
      if (!button || button.disabled) {
        return;
      }
      if (status) {
        status.classList.add("is-running");
        status.textContent = "กำลังรัน ngspice… กรุณารอผลจาก engine";
      }
      button.disabled = true;
      button.textContent = "กำลังรัน ngspice…";
      form.setAttribute("aria-busy", "true");
    });

    window.addEventListener("pageshow", function () {
      if (button) {
        button.disabled = false;
        button.textContent = defaultButtonText;
      }
      if (status) {
        status.classList.remove("is-running");
        status.textContent = defaultStatusText;
      }
      form.removeAttribute("aria-busy");
    });

    updateGroups();
  });
})();
