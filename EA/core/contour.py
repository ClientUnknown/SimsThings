import mathimport sims4.mathHEIGHT = math.sqrt(3)/2POS_INF = float('inf')NEG_INF = float('-inf')EVEN_DELTAS = ((1, 0), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1))ODD_DELTAS = ((1, 0), (1, 1), (0, 1), (-1, 0), (0, -1), (1, -1))DELTAS = (EVEN_DELTAS, ODD_DELTAS)
def _delta_to_ix(ix, iy, dx, dy, nx, ny):
    jx = ix + dx
    jy = iy + dy
    if jx < 0 or (jx >= nx or jy < 0) or jy >= ny:
        return
    index = jx + jy*nx
    return index

def _edge_intercept(vt, vf, value, values, points):
    delta = values[vt] - values[vf]
    delta_t = values[vt] - value
    tf = delta_t/delta
    pt = sims4.math.interpolate(points[vt], points[vf], tf)
    return pt

class HeightField:

    def __init__(self, fn, bounding_rect, spacing):
        self.fn = fn
        self.bounding_rect = bounding_rect
        self.spacing = spacing
        size = self.bounding_rect.b - self.bounding_rect.a
        nx = 1 + math.floor(size.x/spacing)
        ny = 1 + math.floor(size.y/(spacing*HEIGHT))
        self._size = (nx, ny)
        self._points = [None]*(nx*ny)
        self._values = [0]*(nx*ny)
        self._min_value = POS_INF
        self._max_value = NEG_INF
        self._edge_ix = {}
        self._edges = []
        for iy in range(ny):
            for ix in range(nx):
                index = ix + iy*nx
                deltas = DELTAS[iy % 2]
                adj = [_delta_to_ix(ix, iy, dx, dy, nx, ny) for (dx, dy) in deltas]
                for i in range(3):
                    index2 = adj[i]
                    if index2 is None:
                        pass
                    else:
                        cw = adj[(i + 1) % len(adj)]
                        ccw = adj[(i + len(adj) - 1) % len(adj)]
                        self._edge_ix[(index, index2)] = len(self._edges)
                        self._edge_ix[(index2, index)] = len(self._edges)
                        self._edges.append([index, index2, cw, ccw])
        self._sample_points()

    def isolines(self, value):
        edges = [None]*len(self._edges)
        segments = {}
        for (a, b, cw, ccw) in self._edges:
            pa = self._values[a] <= value
            pb = self._values[b] <= value
            if pa != pb:
                edge1 = self._edge_ix[(a, b)]
                if pa:
                    c = cw
                    vt = a
                    vf = b
                else:
                    c = ccw
                    vt = b
                    vf = a
                if edges[edge1] is None:
                    pt = _edge_intercept(vt, vf, value, self._values, self._points)
                    edges[edge1] = pt
                if c is not None:
                    pc = self._values[c] <= value
                    v = vf if pc else vt
                    edge2 = self._edge_ix[(v, c)]
                    segments[edge1] = edge2
        pending = {}
        while segments:
            (e1, e2) = segments.popitem()
            pending[e1] = (e2, [edges[e1], edges[e2]])
        tails = {}
        lines = []
        while pending:
            (e1, (e2, points)) = pending.popitem()
            if e1 == e2:
                points.append(points[0])
                lines.append(points)
            elif e2 in pending:
                (e3, points2) = pending.pop(e2)
                pending[e1] = (e3, points + points2)
            elif e2 in tails:
                (e3, points2) = tails.pop(e2)
                tails[e1] = (e3, points + points2)
            else:
                tails[e1] = (e2, points)
        for (_, points) in tails.values():
            lines.append(points)
        return lines

    def all_isolines(self, spacing=1.0, max_values=10):
        start = math.ceil(self._min_value + 0.1)
        stop = math.floor(self._max_value - 0.1)
        if start > stop:
            return []
        num_values = 1 + math.floor((stop - start)/spacing)
        if num_values > max_values:
            spacing = math.ceil((stop - start)/max_values)
            num_values = 1 + math.floor((stop - start)/spacing)
        result = []
        for i in range(num_values):
            value = start + i*spacing
            for isoline in self.isolines(value):
                result.append((value, isoline))
        return result

    def _sample_points(self):
        half_spacing = self.spacing*0.5
        y_spacing = self.spacing*HEIGHT
        y_offset = self.bounding_rect.a.y
        (nx, ny) = self._size
        for iy in range(ny):
            y = y_offset + y_spacing*iy
            x_offset = self.bounding_rect.a.x + half_spacing*(iy % 2)
            for ix in range(nx):
                x = x_offset + self.spacing*ix
                point = sims4.math.Vector2(x, y)
                value = self.fn(point)
                index = ix + iy*nx
                self._points[index] = point
                self._values[index] = value
                self._max_value = max(self._max_value, value)
                self._min_value = min(self._min_value, value)
