import re


def _split_table_row(row: str) -> list[str]:
    stripped = row.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [
        cell.strip().replace(r"\|", "|") for cell in re.split(r"(?<!\\)\|", stripped)
    ]


def _separator_to_alignment(separator: str) -> str | None:
    normalized = separator.replace(" ", "")
    if not re.fullmatch(r":?-{3,}:?", normalized):
        return None
    if normalized.startswith(":") and normalized.endswith(":"):
        return "center"
    if normalized.startswith(":"):
        return "left"
    if normalized.endswith(":"):
        return "right"
    return None


def render_table_block(block: str) -> str | None:
    lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        return None

    header_cells = _split_table_row(lines[0])
    separator_cells = _split_table_row(lines[1])
    if len(header_cells) == 0 or len(header_cells) != len(separator_cells):
        return None

    alignments = []
    for separator in separator_cells:
        alignment = _separator_to_alignment(separator)
        if alignment is None and separator.replace(" ", "") != "---":
            return None
        alignments.append(alignment)

    body_rows = []
    for line in lines[2:]:
        row_cells = _split_table_row(line)
        if len(row_cells) != len(header_cells):
            return None
        body_rows.append(row_cells)

    def render_cell(tag: str, value: str, alignment: str | None) -> str:
        align_attr = f' style="text-align:{alignment}"' if alignment else ""
        return f"<{tag}{align_attr}>{value}</{tag}>"

    thead = (
        "<thead><tr>"
        + "".join(
            render_cell("th", cell, alignments[i])
            for i, cell in enumerate(header_cells)
        )
        + "</tr></thead>"
    )
    tbody = (
        "<tbody>"
        + "".join(
            "<tr>"
            + "".join(
                render_cell("td", cell, alignments[i]) for i, cell in enumerate(row)
            )
            + "</tr>"
            for row in body_rows
        )
        + "</tbody>"
    )

    return f"<table>{thead}{tbody}</table>"
