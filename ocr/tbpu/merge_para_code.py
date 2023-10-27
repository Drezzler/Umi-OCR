# 合并：段落-横排-代码段（还原空格间距）


from .tbpu import Tbpu


class MergeParaCode(Tbpu):
    def __init__(self):
        super().__init__()
        self.tbpuName = "Multiple lines - code segment"
        self.mllhY = 0.5  # Vertical distance deviation threshold when merging single rows
        self.indentation = 0.5  # When merging multiple lines, indent

    def merge2box(self, A, B):  # Return True when two text blocks belong to the same line
        yTop = min(A[0][1], A[1][1], B[0][1], B[1][1])
        yBottom = max(A[2][1], A[3][1], B[2][1], B[3][1])
        xLeft = min(A[0][0], A[3][0], B[0][0], B[3][0])
        xRight = max(A[1][0], A[2][0], B[1][0], B[2][0])
        A[0][1] = A[1][1] = yTop  # ytop
        A[2][1] = A[3][1] = yBottom  # ybottom
        A[0][0] = A[3][0] = xLeft  # xleft
        A[1][0] = A[2][0] = xRight  # xright

    def mergeLine(self, textBlocks):  # Single row merge
        # All text blocks, sorted by the x coordinate of the upper left corner point
        textBlocks.sort(key=lambda tb: tb["box"][0][0])
        # Traverse each text block, look for items that are vertically close to it in subsequent text blocks, and merge the two text blocks.
        resList = []
        listlen = len(textBlocks)
        for iA in range(listlen):
            tA = textBlocks[iA]
            if not tA:
                continue
            A = tA["box"]
            num = 1  # total number
            # Traverse subsequent text blocks
            for iB in range(iA + 1, listlen):
                tB = textBlocks[iB]
                if not tB:
                    continue
                B = tB["box"]
                Ay = A[1][1]  # The upper right corner y of block A
                Ah = A[3][1] - A[0][1]  # Block A row height
                By = B[0][1]  # Block B upper left corner y
                ly = Ah * self.mllhY
                # If they match the same line, merge
                if abs(By - Ay) < ly:
                    self.merge2box(A, B)
                    tA["text"] += (  # When merging text, add the same number of spaces as the spacing
                            " " * round((A[1][0] - A[0][0]) / (Ah * 2)) + tB["text"]
                    )
                    textBlocks[iB] = None  # Set to empty, mark for deletion
                    num += 1
            if num > 1:
                tA["score"] /= num  # Average confidence
            resList.append(tA)  # Load the results
        return resList

    def mergePara(self, textBlocks):  # Merge all rows
        # Single row merge
        textBlocks = self.mergeLine(textBlocks)
        # Sort by y in the upper left corner
        textBlocks.sort(key=lambda tb: tb["box"][0][1])
        # Extract the indentation length at the beginning of each text block and the average line height.
        leftList = []  # Starting list
        lh = 0
        for tb in textBlocks:
            b = tb["box"]
            leftList.append(b[0][0])
            lh += b[3][1] - b[0][1]
        lh /= len(textBlocks)
        xMin = min(leftList)  # Starting from the leftmost
        xMax = max(leftList)  # End on the far right
        # Build an indentation level list
        levelList = []
        x = xMin
        while x < xMax:
            levelList.append(x)
            x += lh
        levelList.append(xMax + 1)
        # Merge all lines, add leading spaces according to indentation level
        text = ""
        score = 0
        num = 0
        box = None
        for tb in textBlocks:
            # 获取缩进层级
            level = 0
            b = tb["box"]
            for i in range(len(levelList) - 1):
                _min, _max = levelList[i], levelList[i + 1]
                if _min <= b[0][0] < _max:
                    level = i
                    break
            text += " " * level * 2 + tb["text"] + "\n"
            score += tb["score"]
            num += 1
            if not box:
                box = tb["box"]
            else:
                self.merge2box(box, tb["box"])
        if num > 0:
            score /= num
        res = [{"text": text, "box": box, "score": score}]
        # print("= starting list", leftList)
        # print("= level list", levelList)

        return res

    def run(self, textBlocks, imgInfo):
        # Merge paragraphs
        resList = self.mergePara(textBlocks)
        # Return the new block list
        return resList, ""
