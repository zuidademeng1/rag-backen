import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor


def _add_inline_styles(paragraph, text: str):
    """解析行内样式：加粗、斜体、行内代码、链接，添加多个 Run"""
    # 匹配加粗 **text** 或 __text__
    pattern = r"(\*\*(.+?)\*\*|__(.+?)__|`(.+?)`|\[(.+?)\]\((.+?)\)|\*(.+?)\*|_(.+?)_)"
    pos = 0

    for match in re.finditer(pattern, text):
        start, end = match.start(), match.end()

        # 添加普通文本
        if start > pos:
            paragraph.add_run(text[pos:start])

        groups = match.groups()
        if groups[0] and groups[0].startswith("**"):
            run = paragraph.add_run(groups[1])
            run.bold = True
        elif groups[0] and groups[0].startswith("__"):
            run = paragraph.add_run(groups[2])
            run.bold = True
        elif groups[3]:
            run = paragraph.add_run(groups[3])
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(0xE0, 0x6C, 0x75)
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        elif groups[4]:
            run = paragraph.add_run(groups[4])
            run.font.color.rgb = RGBColor(0x03, 0x66, 0xD6)
            run.underline = True
        elif groups[0] and groups[0].startswith("*"):
            run = paragraph.add_run(groups[6])
            run.italic = True
        elif groups[0] and groups[0].startswith("_"):
            run = paragraph.add_run(groups[7])
            run.italic = True

        pos = end

    # 剩余普通文本
    if pos < len(text):
        paragraph.add_run(text[pos:])


def _heading_level(text: str) -> int | None:
    m = re.match(r"^(#{1,6})\s", text)
    return len(m.group(1)) if m else None


def _is_code_fence(line: str) -> bool:
    return line.strip().startswith("```")


def _parse_table_row(line: str) -> list[str] | None:
    if not line.strip().startswith("|") or not line.strip().endswith("|"):
        return None
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def _is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\|[\s\-:|]+\|$", line.strip()))


def _process_inline(text: str) -> str:
    """去掉行内标记符号（处理纯文本段落时使用）"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    return text


def md_to_docx(md_content: str) -> Document:
    """将 Markdown 字符串转换为 python-docx Document 对象"""
    lines = md_content.split("\n")
    doc = Document()

    # 修改默认样式字体
    style = doc.styles["Normal"]
    style.font.name = "微软雅黑"
    style.font.size = Pt(11)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

    # 为列表样式设置字体
    for sname in ["List Bullet", "List Number"]:
        s = doc.styles[sname]
        s.font.name = "微软雅黑"
        s.font.size = Pt(11)
        s._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

    i = 0
    in_code_block = False
    code_lines: list[str] = []
    in_table = False
    table_data: list[list[str]] = []
    table_cols = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 代码块状态切换
        if _is_code_fence(line):
            if in_code_block:
                # 代码块结束，输出
                content = "\n".join(code_lines)
                p = doc.add_paragraph()
                run = p.add_run(content)
                run.font.name = "Consolas"
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(0x24, 0x29, 0x2E)
                # 灰色底色
                shading = run._element.rPr.makeelement(qn("w:shd"), {
                    qn("w:fill"): "F5F5F5",
                    qn("w:val"): "clear",
                })
                run._element.rPr.append(shading)
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(6)
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(stripped)
            i += 1
            continue

        # 空行
        if not stripped:
            if in_table:
                # 表格结束
                in_table = False
                table_data = []
                table_cols = 0
            i += 1
            continue

        # 表格分隔行
        if _is_table_separator(line):
            i += 1
            continue

        # 表格行
        cells = _parse_table_row(line)
        if cells is not None:
            if not in_table:
                in_table = True
                table_data = [cells]
                table_cols = len(cells)
            else:
                table_data.append(cells)
            # 检查下一行是否结束表格
            next_is_empty = i + 1 >= len(lines) or not lines[i + 1].strip()
            next_is_sep = i + 1 < len(lines) and _is_table_separator(lines[i + 1])
            if next_is_empty or next_is_sep:
                # 输出表格
                rows_n = len(table_data)
                cols_n = max(len(r) for r in table_data) if table_data else 0
                if rows_n > 1 and cols_n > 0:
                    t = doc.add_table(rows=rows_n, cols=cols_n)
                    t.style = "Light Grid Accent 1"
                    for ri, row_data in enumerate(table_data):
                        for ci in range(cols_n):
                            val = row_data[ci] if ci < len(row_data) else ""
                            cell = t.cell(ri, ci)
                            cell.text = val
                            for p in cell.paragraphs:
                                p.paragraph_format.space_before = Pt(2)
                                p.paragraph_format.space_after = Pt(2)
                in_table = False
                table_data = []
                table_cols = 0
            i += 1
            continue

        # 标题
        level = _heading_level(line)
        if level is not None:
            p = doc.add_heading(_process_inline(stripped), level=level)
            i += 1
            continue

        # 分割线
        if re.match(r"^[-*_]{3,}\s*$", stripped):
            p = doc.add_paragraph()
            pPr = p._element.get_or_add_pPr()
            pBdr = pPr.makeelement(qn("w:pBdr"), {})
            bottom = pBdr.makeelement(qn("w:bottom"), {
                qn("w:val"): "single",
                qn("w:sz"): "6",
                qn("w:space"): "1",
                qn("w:color"): "CCCCCC",
            })
            pBdr.append(bottom)
            pPr.append(pBdr)
            i += 1
            continue

        # 引用
        if stripped.startswith(">"):
            content = re.sub(r"^>\s?", "", stripped)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(20)
            run = p.add_run(content)
            run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
            run.italic = True
            i += 1
            continue

        # 无序列表
        if re.match(r"^[\-\*\+]\s", stripped):
            content = re.sub(r"^[\-\*\+]\s", "", stripped)
            p = doc.add_paragraph(style="List Bullet")
            _add_inline_styles(p, content)
            i += 1
            continue

        # 有序列表
        if re.match(r"^\d+\.\s", stripped):
            content = re.sub(r"^\d+\.\s", "", stripped)
            p = doc.add_paragraph(style="List Number")
            _add_inline_styles(p, content)
            i += 1
            continue

        # 段落
        p = doc.add_paragraph()
        _add_inline_styles(p, stripped)
        i += 1

    return doc


def md_to_word(md_path: str, output_path: str):
    """将 Markdown 文件转换为 Word 文档"""
    md = Path(md_path).read_text(encoding="utf-8")
    doc = md_to_docx(md)
    doc.save(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python md2word.py <输入.md> <输出.docx>")
        sys.exit(1)

    md_to_word(sys.argv[1], sys.argv[2])
    print(f"转换完成: {sys.argv[1]} → {sys.argv[2]}")
