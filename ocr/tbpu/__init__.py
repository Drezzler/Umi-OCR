# tbpu: text block processing unit
# Text block processing unit

# Among the results returned by OCR, an element containing text, bounding box, and confidence is called a "text block" - text block.
# A text block does not have to be a complete sentence or paragraph. On the contrary, it is usually scattered text.
# An OCR result is often composed of multiple text blocks.
# The text block processor is to process multiple incoming text blocks, such as merging, sorting, and deleting text blocks.


# Concept analysis:
# Column: A page may have single column, double column, or multiple columns. The text blocks between different columns will not be bordered. Text blocks in different columns must not be merged.
# Paragraph: A column may have multiple paragraphs, which may be distinguished by line spacing, starting spaces, etc. How to divide paragraphs and how to merge them, different Tbpu have different solutions.
# Lines: There may be multiple lines within a paragraph. should be combined as much as possible.
# Block: The text block is the smallest unit in the OCR result. One line may be accidentally divided into multiple blocks. This is abnormal and must be merged.


from utils.config import Config
from ocr.tbpu.merge_line import MergeLine
from ocr.tbpu.merge_para import MergePara
from ocr.tbpu.merge_para_code import MergeParaCode
from ocr.tbpu.merge_line_v_lr import TbpuLineVlr
from ocr.tbpu.merge_line_v_rl import TbpuLineVrl

Tbpus = {
    "Single line": MergeLine,
    "Multiple lines - natural paragraph": MergePara,
    "Multi-line-code segment": MergeParaCode,
    "Vertical - left to right - single line": TbpuLineVlr,
    "Vertical - right to left - single line": TbpuLineVrl,
    "No processing": None,
}

Config.set("tbpu", Tbpus)
