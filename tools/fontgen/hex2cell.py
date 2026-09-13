
W_OUT = 12

def load_hex(path, wanted):
    out = {}
    with open(path) as f:
        for line in f:
            code, bits = line.strip().split(":")
            cp = int(code, 16)
            if cp in wanted:
                w = len(bits) // 4 // 16 * 4 if len(bits) == 64 else 8
                rows = [int(bits[i * (len(bits) // 16):(i + 1) * (len(bits) // 16)], 16)
                        for i in range(16)]
                out[cp] = (len(bits) // 16 * 4, rows)
    return out

def runs(row, width):

    s, x = set(), 0
    while x < width:
        if row >> (width - 1 - x) & 1:
            y = x
            while y < width and row >> (width - 1 - y) & 1:
                y += 1
            if y - x >= 2:
                s.update(range(x, y))
            x = y
        else:
            x += 1
    return s

def merge_lines(lines, width, n_out):

    n = len(lines)
    if n <= n_out:
        return lines + [0] * 0
    bits = lambda v: bin(v).count("1")
    hr = [runs(v, width) for v in lines]

    def group_cost(i, j):

        if j - i == 1:
            return 0.0, lines[i]
        acc, andv, c = 0, (1 << width) - 1, 0.0
        for k in range(i, j):
            acc |= lines[k]
            andv &= lines[k]
        c += 3 * bits(acc & ~andv)
        strokes = sum(1 for k in range(i, j) if len(hr[k]) >= 3)
        if strokes >= 2:
            c += 40 * (strokes - 1)
        return c, acc

    def adj_cost(a, b):
        return 3.0 * len(runs(a, width) & runs(b, width))

    INF = float("inf")

    best = {}
    for j in range(1, n + 1):
        c, v = group_cost(0, j)
        best[(1, j)] = (c, None, v)
    for k in range(2, n_out + 1):
        for j in range(k, n + 1):
            cand = (INF, None, 0)
            for i in range(k - 1, j):
                prev = best.get((k - 1, i))
                if prev is None:
                    continue
                c, v = group_cost(i, j)
                tot = prev[0] + c + adj_cost(prev[2], v)
                if tot < cand[0]:
                    cand = (tot, i, v)
            best[(k, j)] = cand
    out, k, j = [], n_out, n
    while k >= 1:
        c, i, v = best[(k, j)]
        out.append(v)
        j = i if i is not None else 0
        k -= 1
    return out[::-1]

def to_cols(rows, width):
    return [sum(((rows[r] >> (width - 1 - c)) & 1) << (len(rows) - 1 - r)
                for r in range(len(rows))) for c in range(width)]

def from_cols(cols, height):
    return [sum(((cols[c] >> (height - 1 - r)) & 1) << (len(cols) - 1 - c)
                for c in range(len(cols))) for r in range(height)]

def crop(rows, width):

    ys = [r for r in range(len(rows)) if rows[r]]
    if not ys:
        return [0], 1
    rows = rows[ys[0]:ys[-1] + 1]
    cols = to_cols(rows, width)
    xs = [c for c in range(width) if cols[c]]
    cols = cols[xs[0]:xs[-1] + 1]
    return from_cols(cols, len(rows)), len(cols)

def hanzi_cell(width, rows):

    rows, w = crop(rows, width)
    rows = merge_lines(rows, w, W_OUT)
    cols = to_cols(rows, w)
    cols = merge_lines(cols, len(rows), W_OUT)
    rows = from_cols(cols, len(rows))
    w = len(cols)
    h = len(rows)
    top = (12 - h) // 2 if h > 11 else 1 + (11 - h) // 2
    left = (12 - w) // 2 if w > 11 else (11 - w) // 2
    out = [0] * 12
    for r, v in enumerate(rows):
        out[top + r] = v << (12 - left - w)
    return out
