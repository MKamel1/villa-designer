"""L2: headless AutoCAD via accoreconsole -- DXF -> DWG -> plotted PDF.

Two things about accoreconsole that cost time to discover, recorded here
so they are not rediscovered:

1. If a script runs out of lines while a command is still prompting, the
   process blocks forever. It does not time out and it does not exit on
   stdin EOF. Every script here must answer every prompt exactly.

2. The -PLOT prompt sequence depends on the output device. With a PDF
   plotter there is NO "write the plot to a file?" prompt -- it goes
   straight to the filename -- and there IS a shade-plot prompt after
   lineweights. Getting this wrong is what causes (1).

The prompt order below was captured from AutoCAD 2026 by running the
command and reading the transcript, not from documentation.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ACCORECONSOLE = Path(
    r"C:\Program Files\Autodesk\AutoCAD 2026\accoreconsole.exe"
)

DEFAULT_DEVICE = "DWG To PDF.pc3"
DEFAULT_PAPER = "ISO full bleed A3 (420.00 x 297.00 MM)"
DEFAULT_CTB = "monochrome.ctb"


class AcadError(RuntimeError):
    pass


def _decode(raw: bytes) -> str:
    """accoreconsole normally emits UTF-16LE, but not on every failure path.

    Decoding blind would turn an error message into mojibake exactly when
    it needs reading, so sniff for the interleaved NUL bytes first.
    """
    if not raw:
        return ""
    sample = raw[:200]
    if sample.count(b"\x00") > len(sample) // 4:
        return raw.decode("utf-16-le", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _run(drawing: Path, script: Path, timeout: int = 300,
         log: Path | None = None) -> str:
    """Run one script against one drawing. Returns the console transcript.

    `log` writes the transcript to a file as well, and -- the reason it
    exists -- makes the transcript readable even when the run is killed on
    timeout. Re-capturing a prompt sequence means reading exactly the output
    that the normal path throws away.
    """
    if not ACCORECONSOLE.exists():
        raise AcadError(f"accoreconsole not found at {ACCORECONSOLE}")
    # Always absolute: given a relative script path accoreconsole neither
    # runs it nor reports an error -- it exits 0 having done nothing, which
    # reads exactly like success.
    drawing, script = Path(drawing).resolve(), Path(script).resolve()
    if not script.exists():
        raise AcadError(f"script not found: {script}")

    proc = subprocess.Popen(
        [str(ACCORECONSOLE), "/i", str(drawing), "/s", str(script)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
    )
    try:
        raw, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Trap 1: a script that under-answers a prompt blocks forever, and
        # the default TimeoutExpired path would leave the child orphaned.
        proc.kill()
        raw, _ = proc.communicate()
        tail = _write_log(log, _decode(raw))
        raise AcadError(
            f"accoreconsole blocked for {timeout}s on {script.name} -- almost "
            f"certainly an unanswered prompt. Re-capture the prompt sequence "
            f"by running it with stdout redirected to a file.{tail}"
        ) from None

    out = _decode(raw)
    _write_log(log, out)
    if proc.returncode != 0:
        raise AcadError(f"accoreconsole exited {proc.returncode}\n{out[-2000:]}")
    return out


def _write_log(log: Path | None, text: str) -> str:
    """Persist a transcript. Returns a short tail to append to an error."""
    if log is None:
        return ""
    log = Path(log).resolve()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(text, encoding="utf-8", errors="replace")
    return f"\nTranscript -> {log}\nlast 600 chars:\n{text[-600:]}"


def _script(path: Path, lines: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return path


def to_dwg(dxf: str | Path, dwg: str | Path, version: str = "2018",
           workdir: Path | None = None) -> Path:
    """Convert a DXF to DWG. Returns the DWG path."""
    dxf, dwg = Path(dxf).resolve(), Path(dwg).resolve()
    dwg.parent.mkdir(parents=True, exist_ok=True)
    # SAVEAS over an existing file asks "already exists, overwrite?", which
    # the script has no answer for -- and an unanswered prompt wedges the
    # process (trap 1). Removing the target first avoids the prompt entirely,
    # which is also what plot_pdf does with its PDF.
    if dwg.exists():
        dwg.unlink()
    scr = _script(
        (workdir or dxf.parent) / "_dxf2dwg.scr",
        ["FILEDIA", "0", "_.SAVEAS", version, str(dwg)],
    )
    _run(dxf, scr)
    if not dwg.exists():
        raise AcadError(f"expected {dwg}, nothing was written")
    return dwg


def plot_pdf(dwg: str | Path, pdf: str | Path, *, device: str = DEFAULT_DEVICE,
             paper: str = DEFAULT_PAPER, ctb: str = DEFAULT_CTB,
             layout: str = "Model", landscape: bool = True,
             workdir: Path | None = None) -> Path:
    """Plot a DWG to PDF, fitted to the sheet. Returns the PDF path."""
    dwg, pdf = Path(dwg).resolve(), Path(pdf).resolve()
    pdf.parent.mkdir(parents=True, exist_ok=True)
    if pdf.exists():
        pdf.unlink()

    scr = _script((workdir or dwg.parent) / "_plot.scr", [
        "FILEDIA", "0",
        "-PLOT",
        "Y",                              # detailed plot configuration
        layout,
        device,
        paper,
        "M",                              # paper units: millimetres
        "L" if landscape else "P",
        "N",                              # plot upside down
        "E",                              # plot area: extents
        "F",                              # scale: fit to paper
        "C",                              # offset: centred
        "Y",                              # plot with plot styles
        ctb,
        "Y",                              # plot with lineweights
        "A",                              # shade plot: As displayed
        str(pdf),                         # filename (no "to file?" prompt)
        "N",                              # save changes to page setup
        "Y",                              # proceed
    ])
    _run(dwg, scr)
    if not pdf.exists():
        raise AcadError(f"plot reported success but {pdf} does not exist")
    return pdf


def plot_layout_pdf(dwg: str | Path, pdf: str | Path, layout: str, *,
                    device: str = DEFAULT_DEVICE, paper: str = DEFAULT_PAPER,
                    ctb: str = DEFAULT_CTB, landscape: bool = True,
                    workdir: Path | None = None, log: Path | None = None) -> Path:
    """Plot a NAMED paper-space layout at 1:1 -- a true-scale sheet, not "fit".

    plot_pdf() above fits model-space extents to the sheet, so whatever scale
    comes out is an accident of the extents (the plot log records 1:30.0048
    for this project). Here the plot area is the Layout and the plot scale is
    1=1, so one paper-space millimetre is one millimetre of paper and the
    drawing's scale is whatever the viewport sets -- see sheet.py.

    The prompt sequence for a layout DIFFERS from Model's, captured from
    AutoCAD 2026 by running it and reading the transcript:

      - the plot-area list offers Layout, not Limits, and the offset prompt
        that follows has NO [Center] option, so "C" -- which plot_pdf() uses
        -- is an invalid answer here and would wedge the process (trap 1);
      - there is NO shade-plot prompt; shade plot is a per-viewport property
        on a layout;
      - three prompts appear that Model never asks: "Scale lineweights with
        plot scale?", "Plot paper space first?" and "Hide paperspace objects?".

    Scaling lineweights is answered No deliberately: at 1:1 it changes
    nothing, and answering Yes would silently rescale pen widths if the sheet
    were ever plotted at another scale.
    """
    dwg, pdf = Path(dwg).resolve(), Path(pdf).resolve()
    pdf.parent.mkdir(parents=True, exist_ok=True)
    if pdf.exists():
        pdf.unlink()

    scr = _script((workdir or dwg.parent) / "_plot_layout.scr", [
        "FILEDIA", "0",
        "-PLOT",
        "Y",                              # detailed plot configuration
        layout,                           # a named layout, not Model
        device,
        paper,
        "M",                              # paper units: millimetres
        "L" if landscape else "P",
        "N",                              # plot upside down
        "Layout",                         # plot area: the layout itself
        "1=1",                            # plot scale: 1 paper mm = 1 drawing unit
        "0,0",                            # offset -- no [Center] option here
        "Y",                              # plot with plot styles
        ctb,
        "Y",                              # plot with lineweights
        "N",                              # scale lineweights with plot scale
        "N",                              # plot paper space first
        "N",                              # hide paperspace objects
        str(pdf),                         # filename (no "to file?" prompt)
        "N",                              # save changes to page setup
        "Y",                              # proceed
    ])
    _run(dwg, scr, log=log)
    if not pdf.exists():
        raise AcadError(f"layout plot reported success but {pdf} does not exist")
    return pdf
