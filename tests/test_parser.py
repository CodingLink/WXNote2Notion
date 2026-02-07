from pathlib import Path
from datetime import date

from wechat_read import parser


def test_parse_sample():
    sample = Path(__file__).parent / "data" / "sample.txt"
    notes, daily = parser.parse_file(sample)
    assert len(notes) == 3

    thought = notes[0]
    assert thought.item_type == "mixed"
    assert thought.created_date == date(2023, 10, 1)
    assert thought.note_text == "今天的灵感真不错"
    assert "原文补充" in (thought.highlight_text or "")

    highlight = notes[1]
    assert highlight.item_type == "highlight"
    assert "第二个高亮" in (highlight.highlight_text or "")

    highlight2 = notes[2]
    assert highlight2.item_type == "highlight"
    assert "第三个高亮" in (highlight2.highlight_text or "")

    assert daily[date(2023, 10, 1)] == 1
