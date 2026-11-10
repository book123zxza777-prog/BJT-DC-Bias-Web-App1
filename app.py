"""Flask routes for the BJT DC bias calculator.

All engineering logic lives in dc_bias.py; this module only parses the form,
formats numbers for display and renders templates.
"""

from __future__ import annotations

from flask import Flask, render_template

app = Flask(__name__)

DEFAULT_VALUES = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
}

DEFAULT_UNITS = {"r1": "kohm", "r2": "kohm", "rc": "kohm", "re": "kohm"}

UNIT_LABELS = {"ohm": "Ω", "kohm": "kΩ", "mohm": "MΩ"}


@app.get("/")
def index():
    return render_template(
        "index.html",
        values=DEFAULT_VALUES,
        units=DEFAULT_UNITS,
        unit_labels=UNIT_LABELS,
        errors={},
        result=None,
    )
