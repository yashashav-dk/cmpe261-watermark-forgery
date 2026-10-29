import importlib.util
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT = Path(__file__).parents[1] / "scripts" / "checkin3_draft.py"
spec = importlib.util.spec_from_file_location("checkin3_draft", SCRIPT)
draft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draft)


def test_table_rows_are_aligned_under_a_header_rule():
    lines = draft.table_lines(
        "| Scheme | Rate |\n|---|---|\n| TR | 6/10 |\n| PRC | 10/10 |"
    )
    assert lines == ["Scheme  Rate ", "-------------", "TR      6/10 ", "PRC     10/10"]


def test_render_adds_one_page_per_saved_figure(tmp_path):
    source = tmp_path / "report.md"
    source.write_text("# Title\n\nText.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    figures = tmp_path / "figures"
    figures.mkdir()
    for name in ["baseline", "imprint"]:
        fig = plt.figure()
        fig.savefig(figures / f"{name}.png")
        plt.close(fig)
    assert draft.render(source, tmp_path / "out.pdf", figures=figures) == 3
    assert draft.render(source, tmp_path / "plain.pdf") == 1


def test_table_caption_stays_with_its_table():
    filler = "\n\n".join(["word " * 80] * 7)
    pages = draft.paginate(filler + "\n\nTable 9. Caption.\n\n" + "\n".join(["| A | B |", "|---|---|"] + ["| 1 | 2 |"] * 12))
    caption_page = next(p for p in pages if any(lines[0].startswith("Table 9.") for lines, _ in p))
    assert any(level == draft.TABLE for _, level in caption_page)
