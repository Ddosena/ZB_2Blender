"""Bl_2_zbr_sclpt (прежнее имя Sculpt Fund: ZBrush Controls, файл sculpt_fund_zbrush.py) — базовое управление
ZBrush в Sculpt Mode Blender 5.2.

Один файл: Preferences → Add-ons → Install from Disk → галочка. При выключении всё возвращается к стандарту.
Что делает (только Sculpt Mode, Object Mode не меняется):
- навигация на ЛКМ по умолчанию отключена (галочка в N → ZBrush / Preferences);
  если включить: протяжка по фону = вращение (Shift во время = оси, Shift-отпустить = крен),
  Alt+протяжка = сдвиг (Alt-отпустить = зум); СКМ = штатное вращение Blender, Shift+СКМ = вращение с осями,
  Alt+СКМ = штатный сдвиг;
- маска (как в ZBrush): Ctrl+протяжка по мешу = кисть маски, с пустого места = рамка Mask Box с крестиком в центре
  (пирог Ctrl+B: Box / Lasso / Line); Ctrl+Alt = стереть; пустая рамка: есть маска — сброс, нет — DynaMesh;
  Ctrl+клик по мешу = блюр, Ctrl+Alt+клик = шарп, Ctrl+клик по фону = инверсия;
- видимость: Ctrl+Shift+протяжка = выбранный инструмент (пирог на Ctrl+Shift+СКМ, индикатор в шапке), пустая
  рамка / лассо = инверсия видимости; Ctrl+Shift+клик: по фону = показать всё, по Face Set = изолировать / скрыть;
  Del Hidden (Tab, панель N) = удалить скрытое;
- быстрый двойной Alt+клик по другому объекту = перейти на него (как сабтул); Shift+A = примитив отдельным объектом;
- Ctrl+Z / Ctrl+Shift+Z в Sculpt не выводят в Object Mode (шаги аддона через Object Mode — разом), симметрию не трогают;
- клавиши ZBrush: пробел = размер, U = сила, O = жёсткость, F = показать модель, Shift+F = цвета Face Sets
  (сетка активного объекта — галочкой в панели N),
  L = Lazy Mouse, X = симметрия вкл / выкл (с прежними осями), B = полка кистей, Q = кисть, W = гизмо (стрелки),
  E = полное гизмо, Tab = Quick Favorites (+ Symmetrize с выбранной стороны, BackfaceMask кисти, Del Hidden),
  D / Shift+D = уровень Multires,
  Ctrl+D = подразделить Multires (сам Multires не добавляется; штатные Ctrl+0…5 отключены), Ctrl+A = замаскировать всё,
  Ctrl+H = показать маску, Ctrl+W = Face Set из маски; Alt+ЛКМ = инверсия кисти;
  1 Crease Sharp, 2 Scrape/Fill, 3 Grab, 4 Clay Strips (и V, C, Shift+T); G / R / S = перенос / поворот / масштаб
  незамаскированного, как в Object Mode, X / Y / Z — по осям гизмо;
- в Sculpt другие объекты чуть темнее (нейтрально, сила — в панели N), таймлайн свёрнут в «Кисти»;
- DynaMesh: Resolution (как в ZBrush) рядом с кнопкой в шапке; Voxel Size — в панели N;
- кисти с Size Pressure: копии Essentials в своей библиотеке (создаются сами); Grab (3) — свой, как Move в ZBrush:
  сфера радиуса кисти у точки нажатия, мимо меша — ближайшее в круге кисти; BackfaceMask — по направлению протяжки;
- гизмо (W / E): центр в центр незамаскированного (и сразу после замены / добавления примитива); Alt+клик и
  Alt+протяжка по мешу = центр по поверхности и оси по её нормали, Alt за стрелку /
  центр гизмо = центр по оси / свободно без меша, Alt за кольцо = поворот осей; Alt+клик по фону = центр
  незамаскированного; протяжка по фону = навигация; Ctrl+протяжка стрелки = копия незамаскированного (вырез из
  меша — выдавливание); иконки над гизмо: Customize (замена примитивом с учётом маски), центр, оси по миру;
  Ctrl+клик по полигруппе = замаскировать всё, кроме неё, гизмо — в её центр; кубик масштаба — точно по оси гизмо;
  оси гизмо запоминаются по состояниям меша и возвращаются Ctrl+Z / Ctrl+Shift+Z;
- полигруппы: Ctrl+W без маски = Group Visible, пирог Alt+W; отделить замаскированное в отдельный объект.
"""

bl_info = {
    "name": "Bl_2_zbr_sclpt",
    "author": "Ddosena",
    "version": (1, 5, 2),
    "blender": (5, 2, 0),
    "location": "3D Viewport > Sculpt Mode",
    "description": "ZBrush-style navigation, gestures, hotkeys, brushes with Size Pressure and primitive replace",
    "doc_url": "https://github.com/Ddosena/ZB_2Blender#readme",
    "tracker_url": "https://github.com/Ddosena/ZB_2Blender/issues",
    "category": "Sculpt",
}

import functools
import math
import os
import time

import bmesh
import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty
from bpy_extras import view3d_utils
from mathutils import Matrix, Quaternion, Vector
from mathutils.geometry import intersect_line_line

# --- константы ------------------------------------------------------------------------------------------

LIB_NAME = "Sculpt Fund Brushes"
CATALOG = "Sculpt fund"
CATALOG_ID = "a9d282e4-000e-4780-b513-ef89dfff98dd"
BRUSHES = ("Crease Sharp", "Scrape/Fill", "Grab", "Clay Strips", "Draw")
ESSENTIALS_FILE = os.path.join("assets", "brushes", "essentials_brushes-mesh_sculpt.blend")
BRUSH_KEYS = (('ONE', False, "Crease Sharp"), ('TWO', False, "Scrape/Fill"), ('THREE', False, "Grab"),
              ('FOUR', False, "Clay Strips"), ('V', False, "Draw"),
              ('C', False, "Clay Strips"), ('T', True, "Scrape/Fill"))       # G — перемещение (21.10.2026), Grab — 3

CS_TOOLS = (
    ('SELECT_LASSO', "Select Lasso", "Оставить видимым то, что внутри лассо (с Alt — скрыть внутри)", 'paint.hide_show_lasso_gesture'),
    ('SELECT_BOX', "Select Box", "Оставить видимым то, что внутри рамки (с Alt — скрыть внутри)", 'paint.hide_show'),
    ('TRIM_LASSO', "Trim Lasso", "Вырезать то, что внутри лассо", 'sculpt.trim_lasso_gesture'),
    ('TRIM_BOX', "Trim Box", "Вырезать то, что внутри рамки", 'sculpt.trim_box_gesture'),
    ('TRIM_LINE', "Trim Line", "Отрезать всё по одну сторону линии (≈ TrimCurve)", 'sculpt.trim_line_gesture'),
    ('LINE_PROJECT', "Line Project", "Сплющить по линии (≈ ClipCurve)", 'sculpt.project_line_gesture'),
    ('LINE_FACE_SET', "Line Face Set", "Новый Face Set по линии (≈ SliceCurve)", 'sculpt.face_set_line_gesture'),
)
CS_OPS = {t[0]: t[3] for t in CS_TOOLS}

# Ctrl, как в ZBrush: по мешу — кисть маски (MaskPen), с пустого места — выбранная фигура (по умолчанию MaskRect)
CTRL_TOOLS = (
    ('MASK_BOX', "Mask Box", "С пустого места — рамка (≈ MaskRect), крестик в центре; Space двигает рамку", "Box"),
    ('MASK_LASSO', "Mask Lasso", "Лассо (≈ MaskLasso) — с пустого места и по мешу; Space двигает лассо", "Lasso"),
    ('MASK_LINE', "Mask Line", "С пустого места — маска по одну сторону линии (≈ MaskCurve)", "Line"),
)
CTRL_NAMES = {t[0]: t[1] for t in CTRL_TOOLS}
CTRL_SHORT = {t[0]: t[3] for t in CTRL_TOOLS}
CS_NAMES = {t[0]: t[1] for t in CS_TOOLS}
# инструменты-гизмо в Sculpt Mode: W — Move (стрелки), E — Transform (стрелки, кольца, масштаб), с панели — Rotate, Scale
GIZMO_TOOLS = {'builtin.move': "3D View Tool: Move", 'builtin.transform': "3D View Tool: Transform",
               'builtin.rotate': "3D View Tool: Rotate", 'builtin.scale': "3D View Tool: Scale"}
GIZMO_ICON_LIFT = 1.95      # ряд иконок над центром гизмо, в размерах гизмо: выше всех ручек (ручки — до ~1,45)

RADIAL_COMMON = {
    'rotation_path': 'tool_settings.sculpt.brush.texture_slot.angle',
    'color_path': 'tool_settings.sculpt.brush.cursor_color_add',
    'image_id': 'tool_settings.sculpt.brush',
}

addon_keymaps = []          # (km, kmi) из addon-раскладки, снимаются при выключении
DISABLED_DEFAULTS = (       # стандартные строки Sculpt, которые мешают: (idname, type, value, ctrl, shift, alt)
    ("sculpt.brush_stroke", 'LEFTMOUSE', 'PRESS', True, False, False),
    ("sculpt.brush_stroke", 'LEFTMOUSE', 'PRESS', True, False, True),
)
SUBDIV_SET_KEYS = ('ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE')     # штатные Ctrl+0…5 object.subdivision_set
ROTATE_MODAL_ITEMS = (      # Legacy 1.3: удалить добавленные аддоном глобальные Shift-привязки.
    ("AXIS_SNAP_ENABLE", 'LEFT_SHIFT', 'PRESS', dict(any=True)),
    ("AXIS_SNAP_DISABLE", 'LEFT_SHIFT', 'RELEASE', dict(any=True)),
    ("AXIS_SNAP_ENABLE", 'MOUSEMOVE', 'ANY', dict(shift=True)),
)


class _Defaults:
    controls_on = True
    ctrl_bg_tool = 'MASK_BOX'
    cs_tool = 'TRIM_LASSO'
    disable_lmb_navigation = True
    use_canvas_masking = True
    use_rmb_nav = False
    split_in_quick = True
    focus_sculpt = True
    polyframe_wire = False
    fade_others = 0.25


def prefs():
    addon = bpy.context.preferences.addons.get(__name__)
    return addon.preferences if addon is not None and addon.preferences is not None else _Defaults


# --- вспомогательное ------------------------------------------------------------------------------------

def brush_dir():
    return bpy.utils.user_resource('DATAFILES', path="sculpt_fund_brushes", create=True)


def brush_file(name):
    return name.replace("/", "_") + ".asset.blend"


def brush_tool_active(context):
    try:
        tool = context.workspace.tools.from_space_view3d_mode('SCULPT', create=False)
    except Exception:
        return True
    return tool is None or tool.idname == 'builtin.brush'


def gizmo_tool_active(context):
    """Режим гизмо: активен один из инструментов с гизмо Transform (W — Move, E — Transform, Rotate, Scale)."""
    try:
        tool = context.workspace.tools.from_space_view3d_mode('SCULPT', create=False)
    except Exception:
        return False
    return tool is not None and tool.idname in GIZMO_TOOLS


def depth_hit(context, event, obj=None):
    return depth_point(context, event, obj) is not None


def depth_point(context, event, obj=None):
    """Точка видимой геометрии под курсором или None (глубина экрана, как у 3D-курсора: GPU, не зависит от числа граней).
    3D-курсор ставится дважды с разных стартовых глубин перед камерой: есть геометрия — обе точки совпадают
    (поверхность), нет — расходятся (каждая ложится на свою плоскость). Не зависит от того, где был 3D-курсор.
    obj задан — точка должна лежать в габаритах этого объекта, другие объекты сцены считаются фоном.
    Скрытые грани не рисуются и считаются фоном."""
    cur = context.scene.cursor
    old = cur.location.copy()
    rv = context.region_data
    dist = max(rv.view_distance, 1e-3)
    view_dir = rv.view_rotation @ Vector((0.0, 0.0, -1.0))
    starts = (rv.view_location.copy(), rv.view_location + view_dir * dist * 0.5)
    hits = []
    try:
        for start in starts:
            cur.location = start
            bpy.ops.view3d.cursor3d('INVOKE_DEFAULT', use_depth=True, orientation='NONE')
            hits.append(cur.location.copy())
    except RuntimeError:
        return None
    finally:
        cur.location = old
    if (hits[0] - hits[1]).length > dist * 1e-4:
        return None
    p = hits[0]
    if obj is not None:
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        lo = Vector((min(q[i] for q in pts) for i in range(3)))
        hi = Vector((max(q[i] for q in pts) for i in range(3)))
        pad = max((hi - lo).length * 0.02, dist * 1e-4)
        if any(p[i] < lo[i] - pad or p[i] > hi[i] + pad for i in range(3)):
            return None
    return p


def visible_face_sets(obj):
    """Множество Face Set среди видимых граней (numpy, без цикла по граням в Python). None — нельзя прочитать."""
    import numpy as np
    me = obj.data
    n = len(me.polygons)
    if obj.use_dynamic_topology_sculpting or n == 0:
        return None
    fs = me.attributes.get(".sculpt_face_set")
    hp = me.attributes.get(".hide_poly")
    sets = np.ones(n, dtype=np.int32)
    hidden = np.zeros(n, dtype=bool)
    if fs is not None and len(fs.data) == n:
        fs.data.foreach_get("value", sets)
    if hp is not None and len(hp.data) == n:
        hidden_i = np.zeros(n, dtype=bool)
        hp.data.foreach_get("value", hidden_i)
        hidden = hidden_i
    return bool(hidden.any()), set(np.unique(sets[~hidden]).tolist())


def face_under_cursor(context, event, obj):
    """Индекс видимой грани obj под пером или None (под пером не этот меш). Точка видимой поверхности — по глубине
    экрана (depth_point), грань — ближайшая к ней среди граней у ближайших вершин (numpy, без BVH: после мазков
    BVH пришлось бы строить заново, на миллионе граней это ~0,5 с)."""
    import numpy as np
    from mathutils.geometry import intersect_point_tri, normal as poly_normal
    p = depth_point(context, event, obj)
    if p is None:
        return None
    me = obj.data
    nv, nf = len(me.vertices), len(me.polygons)
    if nv == 0 or nf == 0:
        return None
    co = np.empty(nv * 3, dtype=np.float32)
    me.attributes["position"].data.foreach_get("vector", co)
    co = co.reshape(nv, 3)
    P = obj.matrix_world.inverted_safe() @ p
    d2 = ((co - np.array(P, dtype=np.float32)) ** 2).sum(axis=1)
    d2[read_attr(me, ".hide_vert", nv, bool, False)] = np.inf
    k = min(12, nv)
    near = np.argpartition(d2, k - 1)[:k]
    starts, totals, cv = face_vertex_arrays(me)
    faces = np.unique(np.repeat(np.arange(nf), totals)[np.isin(cv, near)])
    faces = faces[~read_attr(me, ".hide_poly", nf, bool, False)[faces]]
    best, best_score = None, None
    for f in faces.tolist():
        vs = [Vector(co[i].tolist()) for i in cv[starts[f]:starts[f] + totals[f]]]
        if len(vs) < 3:
            continue
        c = sum(vs, Vector()) / len(vs)
        n = poly_normal(vs)
        q = P - n * n.dot(P - c)
        inside = any(intersect_point_tri(q, vs[0], vs[i], vs[i + 1]) is not None for i in range(1, len(vs) - 1))
        score = (not inside, abs(n.dot(P - c)), (q - c).length)
        if best_score is None or score < best_score:
            best, best_score = f, score
    return best


def mask_all_but_face_set(context, event, report=None):
    """Режим гизмо: Ctrl+клик по полигруппе — маска на всём, кроме неё (как в ZBrush), гизмо — в её центр. None —
    под пером нет активного меша (дальше как по фону). Вершины на границе группы — её: без маски (раньше маскировались,
    и узкая или маленькая группа не двигалась вовсе — гизмо ехало без меша, 21.10.2026). Один шаг истории: его пишет
    штатная инверсия маски (Sculpt-шаг помнит маску до неё), затем итоговая маска пишется напрямую; Ctrl+Z вернёт
    прежнюю маску, Ctrl+Shift+Z — эту (t55)."""
    import numpy as np
    obj = context.active_object
    if not mesh_readable(obj) or obj.modifiers or obj.data.shape_keys:
        if report is not None:
            report({'WARNING'}, "Маска по полигруппе: нужен меш без Dyntopo, Multires, Shape Keys и модификаторов")
        return {'CANCELLED'}
    face = face_under_cursor(context, event, obj)
    if face is None:
        return None
    me = obj.data
    nv, nf = len(me.vertices), len(me.polygons)
    sets = read_attr(me, ".sculpt_face_set", nf, np.int32, 1)
    group = (sets == sets[face]) & ~read_attr(me, ".hide_poly", nf, bool, False)
    _starts, totals, cv = face_vertex_arrays(me)
    old = read_attr(me, ".sculpt_mask", nv, np.float32, 0.0)
    new = old.copy()
    new[~read_attr(me, ".hide_vert", nv, bool, False)] = 1.0        # скрытые не трогает и штатная инверсия
    new[np.unique(cv[np.repeat(group, totals)])] = 0.0
    if not np.array_equal(old, new):
        if safe(bpy.ops.paint.mask_flood_fill, 'EXEC_DEFAULT', True, mode='INVERT', report=report) == {'CANCELLED'}:
            return {'CANCELLED'}
        me.attributes[".sculpt_mask"].data.foreach_set("value", new)
        me.update()
    set_pivot_unmasked(context, report)
    return {'FINISHED'}


def has_mask(obj):
    """Есть ли маска (True, если прочитать нельзя: Dyntopo / Multires)."""
    import numpy as np
    if not mesh_readable(obj):
        return True
    me = obj.data
    return bool((read_attr(me, ".sculpt_mask", len(me.vertices), np.float32, 0.0) > 0.0).any())


def safe(op, *args, report=None, **kw):
    """Вызов оператора без падения: при ошибке контекста — сообщение в статус-баре, а не трейсбек."""
    try:
        return op(*args, **kw)
    except (RuntimeError, TypeError) as e:
        if report is not None:
            report({'WARNING'}, str(e).splitlines()[0][:200])
        return {'CANCELLED'}


def axis_aligned_quats():
    quats = []
    axes = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    import itertools
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            m = Matrix([axes[perm[i]] * signs[i] for i in range(3)]).transposed()
            if abs(m.determinant() - 1) < 1e-6:
                quats.append(m.to_quaternion())
    return quats


AXIS_QUATS = axis_aligned_quats()


def snap_quat(q):
    return max(AXIS_QUATS, key=lambda a: abs(a.dot(q))).copy()


# --- центр гизмо Transform (W) --------------------------------------------------------------------------
# Центр гизмо скульпта (pivot) Blender держит у себя и в Python не отдаёт. Аддон ведёт его сам, в координатах объекта,
# как Blender: при каждой своей установке (W, Alt, иконка, Shift+ПКМ), после перемещения гизмо (TRANSFORM_OT_translate
# сдвигает центр на value) и при нажатии на ручку гизмо (там центр читается точно). Новый сеанс Sculpt Mode
# (смена режима, другой объект) начинается с центром в начале координат объекта. После Ctrl+Z / Ctrl+Shift+Z центр
# заново ставится в центр незамаскированного (Blender возвращает центр шага отмены, Python его не видит).

_pivot = {"key": None, "co": None, "op": 0, "busy": False, "alt": None, "alt_undone": False}
_gizmo_press = [0.0, 0, 0]      # время и место последнего нажатия на ручку гизмо


def last_op_ptr():
    ops = bpy.context.window_manager.operators
    return ops[-1].as_pointer() if len(ops) else 0


def pivot_key(obj):
    return (obj.name, obj.as_pointer())


def pivot_local(obj):
    if _pivot["key"] != pivot_key(obj) or _pivot["co"] is None:
        queue_gizmo_orientation_reset(bpy.context)
        _pivot.update(key=pivot_key(obj), co=Vector(), op=last_op_ptr())
    return _pivot["co"]


def pivot_store(obj, co_local):
    _pivot.update(key=pivot_key(obj), co=Vector(co_local), op=last_op_ptr())


def mesh_readable(obj):
    """Атрибуты меша в Sculpt Mode актуальны: не Dyntopo и не Multires (у них свои данные)."""
    return obj is not None and obj.type == 'MESH' and not obj.use_dynamic_topology_sculpting and multires(obj) is None


def read_attr(me, name, n, dtype, default):
    import numpy as np
    out = np.full(n, default, dtype=dtype)
    a = me.attributes.get(name)
    if a is not None and len(a.data) == n:
        a.data.foreach_get("value", out)
    return out


def unmasked_center_local(obj):
    """Повтор расчёта sculpt.set_pivot_position(UNMASKED) Blender 5.2 без симметрии (сверено тестом t17): среднее
    видимых вершин с весом 1 − маска. None — незамаскированного нет, Blender оставляет центр на месте."""
    import numpy as np
    me = obj.data
    n = len(me.vertices)
    if n == 0:
        return None
    if obj.use_dynamic_topology_sculpting:      # меш в BMesh, данные объекта устарели: приблизительно — центр габаритов
        return sum((Vector(c) for c in obj.bound_box), Vector()) / 8
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3).astype(np.float64)
    w = np.ones(n) if multires(obj) is not None else 1.0 - read_attr(me, ".sculpt_mask", n, np.float32, 0.0)
    w[read_attr(me, ".hide_vert", n, bool, False)] = 0.0
    s = w.sum()
    if s <= 0.0:
        return None
    return Vector(((co * w[:, None]).sum(axis=0) / s).tolist())


def set_pivot_unmasked(context, report=None):
    """Центр гизмо в центр незамаскированного (штатный оператор) и запись его в отслеживание.
    С симметрией Blender берёт только вершины со стороны прежнего центра, а тот после отмены через шаг сцены
    сбрасывается в начало координат — поэтому на время вызова симметрия выключается: центр всего незамаскированного,
    как в ZBrush, и не зависит от прежнего центра."""
    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return {'CANCELLED'}
    prev = pivot_local(obj).copy()
    me = obj.data
    mirror = (me.use_mirror_x, me.use_mirror_y, me.use_mirror_z)
    if any(mirror):
        me.use_mirror_x = me.use_mirror_y = me.use_mirror_z = False
    try:
        res = safe(bpy.ops.sculpt.set_pivot_position, mode='UNMASKED', report=report)
    finally:
        if any(mirror):
            me.use_mirror_x, me.use_mirror_y, me.use_mirror_z = mirror
    if res != {'CANCELLED'}:
        c = unmasked_center_local(obj)
        pivot_store(obj, c if c is not None else prev)
    return res


def translate_delta_local(obj, op):
    """Сдвиг центра гизмо от TRANSFORM_OT_translate в координатах объекта."""
    p = op.properties
    d = Vector(p.value)
    if p.orient_type != 'GLOBAL':
        d = Matrix(p.orient_matrix) @ d
    return obj.matrix_world.to_3x3().inverted_safe() @ d


def pivot_screen(context):
    """Экранная точка центра гизмо для ряда иконок или None (не показывать)."""
    obj = context.active_object
    if obj is None or obj.type != 'MESH' or _pivot["busy"]:
        return None
    win = context.window
    if win is not None:
        for modal in win.modal_operators:
            if modal.bl_idname.startswith("TRANSFORM_OT"):
                capture_gizmo_rotation_view(context, modal)
                return None
    co = pivot_local(obj)
    ptr = last_op_ptr()
    if ptr != _pivot["op"]:
        ops = context.window_manager.operators
        op = ops[-1] if len(ops) else None      # после Ctrl+Z список операций бывает пустым
        if op is not None and op.bl_idname == 'TRANSFORM_OT_translate':
            co = co + translate_delta_local(obj, op)
            _pivot["co"] = co
        elif op is not None and op.bl_idname in {'TRANSFORM_OT_rotate', 'TRANSFORM_OT_trackball'}:
            queue_gizmo_rotation(context, op)
        if op is not None and op.bl_idname != 'SCULPT_FUND_OT_gizmo_moved':
            _pivot["alt"] = None        # после Alt-переноса было другое действие: Ctrl+Z отменит уже его
        _pivot["op"] = ptr
    return view3d_utils.location_3d_to_region_2d(context.region, context.region_data, obj.matrix_world @ co)


ALT_KEY_CHECK = True     # тесты с выдуманными событиями выключают: там Alt на клавиатуре не нажат


def alt_held(event):
    """Alt по событию Blender, а в Windows ещё и по клавиатуре прямо сейчас. Blender бывает уверен, что Alt зажат,
    когда его уже отпустили (отпускание пришло, пока окно было не в фокусе), — тогда протяжка гизмо двигала только
    гизмо, «как с Alt» (21.10.2026). Нажатие Alt кнопкой пера или экспресс-клавишей драйвер шлёт как настоящее."""
    if not event.alt:
        return False
    if not ALT_KEY_CHECK or os.name != 'nt':
        return True
    try:
        import ctypes
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000)     # VK_MENU, любой Alt
    except (AttributeError, OSError):
        return True


def gizmo_pressed(event):
    """Это нажатие уже пришло на ручку гизмо (строка в раскладке гизмо отметила его раньше)."""
    t, x, y = _gizmo_press
    return time.perf_counter() - t < 0.3 and (x, y) == (event.mouse_x, event.mouse_y)


def view3d_override():
    wm = bpy.context.window_manager
    for win in wm.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                region = next((r for r in area.regions if r.type == 'WINDOW'), None)
                if region is not None:
                    return dict(window=win, area=area, region=region)
    return None


def _resync_pivot():
    """Таймер после Ctrl+Z / Ctrl+Shift+Z в режиме гизмо: центр гизмо в центр незамаскированного (известное положение)."""
    try:
        ov = view3d_override()
        if ov is None or prefs() is _Defaults or not prefs().controls_on:
            return None
        with bpy.context.temp_override(**ov):
            if bpy.context.mode == 'SCULPT' and gizmo_tool_active(bpy.context):
                set_pivot_unmasked(bpy.context)
    except (RuntimeError, ReferenceError, TypeError, AttributeError) as e:
        print("Sculpt Fund: pivot resync:", e)
    return None


# Симметрия, как в ZBrush, — не часть истории: X включает / выключает её с теми осями, что были до выключения, а Ctrl+Z /
# Ctrl+Shift+Z её не меняют. Blender хранит оси в меше: шаг Object Mode (вход в Sculpt, шаги аддона) при отмене
# возвращал оси того времени — «Ctrl+Z сбрасывает ось симметрии» (21.10.2026). Перед отменой оси активного меша
# запоминаются и сразу после неё ставятся обратно.
_symmetry = {"memory": {}, "last": (True, False, False), "before": None, "compound": False}


def mirror_axes(me):
    return (bool(me.use_mirror_x), bool(me.use_mirror_y), bool(me.use_mirror_z))


def set_mirror_axes(me, axes):
    if mirror_axes(me) != tuple(axes):
        me.use_mirror_x, me.use_mirror_y, me.use_mirror_z = axes


@persistent
def _on_undo_pre(*_args):
    try:
        obj = bpy.context.view_layer.objects.active
        # внутри составного Ctrl+Z (sculpt_undo) — и на промежуточных шагах Object Mode; вне Sculpt — как в Blender
        _symmetry["before"] = (obj.data.name, mirror_axes(obj.data)) if obj is not None and obj.type == 'MESH' \
            and (obj.mode == 'SCULPT' or _symmetry["compound"]) and prefs().controls_on else None
    except (AttributeError, ReferenceError, RuntimeError):
        _symmetry["before"] = None


def restore_symmetry():
    saved, _symmetry["before"] = _symmetry["before"], None
    if saved is None:
        return
    try:
        me = bpy.data.meshes.get(saved[0])
        if me is not None:
            set_mirror_axes(me, saved[1])
    except (AttributeError, ReferenceError, RuntimeError) as e:
        print("Sculpt Fund: symmetry after undo:", e)


# Короткая надпись по центру вида (как в ZBrush): X меняет симметрию — видно сразу, а не только в строке состояния.
# Зеркальные точки кисти Blender рисует у ближайшей к перу вершины и только если она внутри круга кисти: на редкой
# сетке (куб из 8 вершин) их почти не видно (22.10.2026).
_view_msg = {"handle": None, "text": "", "until": 0.0}


def _draw_view_msg():
    if time.perf_counter() > _view_msg["until"] or bpy.context.region is None:
        return
    import blf
    region = bpy.context.region
    ui = bpy.context.preferences.system.ui_scale
    text = _view_msg["text"]
    blf.size(0, 20 * ui)
    width = blf.dimensions(0, text)[0]
    x, y = (region.width - width) / 2, region.height - 110 * ui
    for dx, dy, color in ((1.5 * ui, -1.5 * ui, (0.0, 0.0, 0.0, 0.7)), (0.0, 0.0, (1.0, 1.0, 1.0, 0.95))):
        blf.color(0, *color)
        blf.position(0, x + dx, y + dy, 0)
        blf.draw(0, text)


def _redraw_views():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def _end_view_msg():
    left = _view_msg["until"] - time.perf_counter()
    if left > 0.0:
        return left
    if _view_msg["handle"] is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_view_msg["handle"], 'WINDOW')
        _view_msg["handle"] = None
    _redraw_views()
    return None


def view_message(text, seconds=1.5):
    _view_msg.update(text=text, until=time.perf_counter() + seconds)
    if _view_msg["handle"] is None:
        _view_msg["handle"] = bpy.types.SpaceView3D.draw_handler_add(_draw_view_msg, (), 'WINDOW', 'POST_PIXEL')
    if not bpy.app.timers.is_registered(_end_view_msg):
        bpy.app.timers.register(_end_view_msg, first_interval=seconds)
    _redraw_views()


class SCULPTFUND_OT_symmetry(bpy.types.Operator):
    """X: симметрия вкл / выкл, как в ZBrush. Включается с теми осями, что были до выключения (впервые — X). Не шаг
    истории: Ctrl+Z симметрию не трогает"""
    bl_idname = "sculpt_fund.symmetry"
    bl_label = "Symmetry On/Off"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        me = context.active_object.data
        axes = mirror_axes(me)
        if any(axes):
            _symmetry["memory"][me.name] = axes
            _symmetry["last"] = axes
            set_mirror_axes(me, (False, False, False))
            text = "Симметрия выключена"
        else:
            axes = _symmetry["memory"].get(me.name, _symmetry["last"])
            set_mirror_axes(me, axes)
            text = "Симметрия: " + " ".join(a for a, on in zip("XYZ", axes) if on)
        self.report({'INFO'}, text)
        view_message(text)
        for area in context.screen.areas:
            area.tag_redraw()       # кнопки X Y Z в шапке
        return {'FINISHED'}


# Ctrl+Z / Ctrl+Shift+Z в Sculpt никогда не выводят в Object Mode (туда — только мышкой, 21.10.2026). Действия аддона,
# которым нужен Object Mode (Shift+A, отделить, Del Hidden, Customize, Merge Down, копия гизмо), пишут три шага:
# Object Mode → действие → Sculpt; Ctrl+Z проходит их разом. В начале сеанса Sculpt дальше только Object Mode — тогда
# история возвращается на место и Ctrl+Z ничего не делает (подсказка в строке состояния). Python не видит список шагов,
# поэтому так: шаг, пока не Sculpt — ещё шаг (не больше UNDO_SCULPT_LIMIT), не вышло — столько же назад.
UNDO_SCULPT_LIMIT = 8
# Метка шагов Object Mode внутри действий аддона (свойство сцены, его хранит и возвращает история): Ctrl+Z проходит
# разом только такие шаги. Шаги Object Mode без метки — работа пользователя (или вход в Sculpt): их Ctrl+Z из Sculpt
# не трогает.
STEP_MARK = "sculpt_fund_inner_step"
_history_queue = []


def mark_inner_steps(scene, on):
    try:
        if on:
            scene[STEP_MARK] = 1
        elif STEP_MARK in scene:
            del scene[STEP_MARK]
    except (ReferenceError, TypeError, KeyError, AttributeError) as e:
        print("Sculpt Fund: step mark:", e)


def _history_step(direction):
    try:
        return (bpy.ops.ed.redo if direction > 0 else bpy.ops.ed.undo)() == {'FINISHED'}
    except RuntimeError:
        return False


def sculpt_history_step(direction):
    """−1 — Ctrl+Z, +1 — Ctrl+Shift+Z. True — шаг сделан и снова Sculpt; False — истории в Sculpt дальше нет."""
    _symmetry["compound"] = True
    try:
        if not _history_step(direction):
            return False
        done = 1
        # Первый шаг Object Mode метку не показывает: отмена входа в Sculpt не перечитывает сцену из истории (t55).
        # Дальше — только помеченные шаги; два непомеченных подряд — это уже работа пользователя в Object Mode
        while (bpy.context.mode != 'SCULPT' and done < UNDO_SCULPT_LIMIT
               and (done == 1 or bpy.context.scene.get(STEP_MARK))):
            if not _history_step(direction):
                break
            done += 1
        if bpy.context.mode == 'SCULPT':
            return True
        for _ in range(done):
            _history_step(-direction)
        return False
    finally:
        _symmetry["compound"] = False


def flash_status(window, text, seconds=2.5):
    try:
        with bpy.context.temp_override(window=window):
            window.workspace.status_text_set(text)
    except (RuntimeError, ReferenceError, AttributeError, TypeError) as e:
        print("Sculpt Fund:", text, e)
        return

    def clear():
        try:
            with bpy.context.temp_override(window=window):
                window.workspace.status_text_set(None)
        except (RuntimeError, ReferenceError, AttributeError, TypeError):
            pass
        return None
    bpy.app.timers.register(clear, first_interval=seconds)


def _run_history():
    """Таймер: шаги истории — вне оператора (отмена файла целиком внутри работающего оператора небезопасна)."""
    queue = list(_history_queue)
    _history_queue.clear()
    try:
        ov = view3d_override()
        if ov is None:
            return None
        with bpy.context.temp_override(**ov):
            for direction in queue:
                if bpy.context.mode != 'SCULPT':
                    break
                if not sculpt_history_step(direction):
                    flash_status(ov["window"], ("Ctrl+Z" if direction < 0 else "Ctrl+Shift+Z") +
                                 ": дальше история — уже Object Mode (в него — только мышкой)")
                    break
    except (RuntimeError, ReferenceError, TypeError, AttributeError) as e:
        print("Sculpt Fund: undo:", e)
    return None


class SCULPTFUND_OT_history(bpy.types.Operator):
    """Ctrl+Z / Ctrl+Shift+Z в Sculpt без выхода в Object Mode: шаги аддона через Object Mode — разом"""
    bl_idname = "sculpt_fund.history"
    bl_label = "Undo / Redo in Sculpt"

    redo: BoolProperty(default=False, options={'SKIP_SAVE'})

    def invoke(self, context, event):
        if context.mode != 'SCULPT' or not prefs().controls_on:
            return {'PASS_THROUGH'}         # вне Sculpt — штатные Ctrl+Z / Ctrl+Shift+Z
        _history_queue.append(1 if self.redo else -1)
        if not bpy.app.timers.is_registered(_run_history):
            bpy.app.timers.register(_run_history, first_interval=0.0)
        return {'FINISHED'}


def _undo_redo(is_undo):
    """Перенос центра Alt'ом — свой шаг истории, Blender отменяет его точно (центр — каким был до шага), повтор
    оставляет центр там же. Это знаем — центр не трогаем; во всех остальных случаях — центр незамаскированного."""
    restore_symmetry()
    try:
        if bpy.context.mode == 'SCULPT':
            # Повтор шага Sculpt после шагов аддона оставляет их метку в сцене (её снимает только история Object Mode):
            # иначе она попала бы в следующий шаг Object Mode пользователя
            mark_inner_steps(bpy.context.scene, False)
    except (AttributeError, ReferenceError, RuntimeError):
        pass
    # Pending rotation-follow callbacks belong to the state before Undo/Redo; the axes come from the history instead.
    _pivot['orient_epoch'] = _pivot.get('orient_epoch', 0) + 1
    _pivot.pop('rot_view', None)
    if not bpy.app.timers.is_registered(_restore_orientation):
        bpy.app.timers.register(_restore_orientation, first_interval=0.0)
    alt = _pivot.get("alt")         # снимается при любой другой операции в режиме гизмо и вне его (pivot_screen, poll)
    if alt is not None and _pivot["co"] is not None:
        pre, post = alt[0], alt[1]
        if is_undo and (_pivot["co"] - post).length < 1e-6:
            _pivot["co"] = pre.copy()
            _pivot["alt_undone"] = True
            return
        if not is_undo and _pivot.get("alt_undone"):
            _pivot["alt_undone"] = False
            return
    _pivot["alt"] = None
    if _pivot["key"] is not None and not bpy.app.timers.is_registered(_resync_pivot):
        bpy.app.timers.register(_resync_pivot, first_interval=0.0)


@persistent
def _on_undo(*_args):
    _undo_redo(True)


@persistent
def _on_redo(*_args):
    _undo_redo(False)


@persistent
def _on_load_pre(*_args):
    global _focus_last
    # Especially important for open_mainfile(load_ui=False): those same editor
    # objects survive the load, so restore their baseline before clearing it.
    restore_focus()
    _focus_last = None
    set_polyframe_wires(False)
    _poly_wire.clear()


@persistent
def _on_save_pre(*_args):
    """В файл — обычный вид: пол, сетка и оси включены, временной сетки Polyframe на объектах нет. Иначе файл,
    сохранённый в Sculpt, откроется со скрытой сеткой (в том числе без аддона)."""
    for _win, _screen, _area, space, values in list(_focus_views.values()):
        try:
            show_focus_overlays(space)
            for prop, value in values["overlay"].items():
                setattr(space.overlay, prop, value)
            space.show_gizmo = values.get("gizmo", True)
        except (ReferenceError, RuntimeError, AttributeError):
            pass
    set_polyframe_wires(False)
    for scene in bpy.data.scenes:
        mark_inner_steps(scene, False)


@persistent
def _on_save_post(*_args):
    for _win, _screen, _area, space, _values in list(_focus_views.values()):
        try:
            apply_focus_overlay(space)
        except (ReferenceError, RuntimeError, AttributeError):
            pass
    set_polyframe_wires(True)


@persistent
def _on_load(*_args):
    _pivot.pop("auto_orient", None)
    _pivot.pop("rot_view", None)
    _pivot["orient_epoch"] = _pivot.get("orient_epoch", 0) + 1
    _pivot.update(key=None, co=None, op=0, busy=False, alt=None, alt_undone=False)
    _orient_hist.clear()
    _focus_views.clear()
    _focus_timelines.clear()
    _timeline_restored.clear()
    _poly_wire.clear()
    _dim["batches"].clear()
    subscribe_focus()
    queue_focus_update()


def pivot_only_move(context, delta_world, report=None):
    """Сдвинуть только центр гизмо, меш на месте. Blender не умеет ставить центр гизмо скульпта в точку, а перенос
    двигает и меш. Поэтому перенос делается в режиме Radius Elastic с кистью 1 px, а на время вызова (без перерисовки)
    вид — ортографический с крошечным масштабом: радиус упругости ~1e-7 размера, вершины не двигаются (t28: сдвиг
    ≤ 3e-8 даже с центром на вершине; 3–5 мс на 0,5 млн граней). Один шаг истории — Ctrl+Z возвращает центр."""
    obj = context.active_object
    sc = context.scene.tool_settings.sculpt
    rv = context.region_data
    brush = sc.brush
    if obj is None or brush is None or rv is None:
        return {'CANCELLED'}
    ups = sc.unified_paint_settings
    unified = ups.use_unified_size
    holder = ups if unified else brush
    saved = (sc.transform_mode, holder.size, getattr(holder, "use_locked_size", None),
             rv.view_perspective, rv.view_distance)
    pre = pivot_local(obj).copy()
    try:
        sc.transform_mode = 'RADIUS_ELASTIC'
        holder.size = 1
        if saved[2] is not None:
            holder.use_locked_size = 'VIEW'
        rv.view_perspective = 'ORTHO'
        rv.view_distance = 1e-5
        res = safe(bpy.ops.transform.translate, 'EXEC_DEFAULT', True, value=tuple(delta_world), orient_type='GLOBAL',
                   constraint_axis=(False, False, False), report=report)
    finally:
        sc.transform_mode = saved[0]
        holder.size = saved[1]
        if saved[2] is not None:
            holder.use_locked_size = saved[2]
        rv.view_perspective, rv.view_distance = saved[3], saved[4]
    if res != {'CANCELLED'}:
        # последней операцией — пустая своя: панель «повторить последнее» не должна предлагать штатный Move
        # (undo=True — только чтобы вызов из Python попал в список операций; шага истории у неё нет)
        safe(bpy.ops.sculpt_fund.gizmo_moved, 'EXEC_DEFAULT', True)
        post = pre + obj.matrix_world.to_3x3().inverted_safe() @ Vector(delta_world)
        pivot_store(obj, post)
        _pivot["alt"] = (pre, post.copy(), last_op_ptr())
        _pivot["alt_undone"] = False
    return res


GIZMO_ORIENT = "ZBrush Gizmo"


def orientation_matrix(context):
    """Оси гизмо сейчас (мировые, 3x3) — по слоту ориентации сцены."""
    slot = context.scene.transform_orientation_slots[0]
    custom = slot.custom_orientation
    obj = context.active_object
    if custom is not None:
        return custom.matrix.copy()
    t = slot.type
    if t == 'VIEW' and context.region_data is not None:
        return context.region_data.view_rotation.to_matrix()
    if t == 'CURSOR':
        return context.scene.cursor.matrix.to_3x3().normalized()
    if t in ('LOCAL', 'NORMAL', 'GIMBAL', 'PARENT') and obj is not None:
        return obj.matrix_world.to_3x3().normalized()
    return Matrix.Identity(3)


def ensure_gizmo_orientation(context, matrix):
    """Своя ориентация «ZBrush Gizmo» с заданной матрицей, выбранная в слоте (для поворота осей Alt'ом)."""
    slot = context.scene.transform_orientation_slots[0]
    if slot.custom_orientation is None or slot.custom_orientation.name != GIZMO_ORIENT:
        safe(bpy.ops.transform.create_orientation, name=GIZMO_ORIENT, use_view=True, use=True, overwrite=True)
    slot = context.scene.transform_orientation_slots[0]
    if slot.custom_orientation is not None:
        slot.custom_orientation.matrix = matrix
    return slot.custom_orientation


# Alt по мешу в режиме гизмо: центр в точку под пером, оси — по нормали поверхности (как Alt+клик в ZBrush).
# Нормаль — numpy, данные один раз на протяжку. До SURFACE_EXACT_FACES граней — по граням: ровно нормаль грани под
# пером (куб, примитивы). Плотная сетка — по нормалям вершин в круге SURFACE_NORMAL_PX вокруг точки: сглаженная, мелкая
# фактура не дёргает оси, и без чтения топологии (оно стоило бы ~0,5 с на 1,3 млн граней; так — ~15 мс, t51).
SURFACE_NORMAL_PX = 6.0
SURFACE_EXACT_FACES = 50000


def surface_cache(obj):
    """('FACES', центры, радиусы до дальней вершины, нормали) видимых граней или ('VERTS', позиции, нормали) вершин —
    всё в мировых координатах; None — меш пуст."""
    import numpy as np
    me = obj.data
    nf, nv = len(me.polygons), len(me.vertices)
    if nf == 0:
        return None
    W = np.array(obj.matrix_world, dtype=np.float64)
    co = np.empty(nv * 3, dtype=np.float32)
    me.attributes["position"].data.foreach_get("vector", co)
    co = co.reshape(nv, 3) @ W[:3, :3].T.astype(np.float32) + W[:3, 3].astype(np.float32)
    to_world = np.linalg.inv(W[:3, :3]).astype(np.float32)      # нормаль в мир: (W⁻¹)ᵀ n, для строк — n @ W⁻¹
    if nf > SURFACE_EXACT_FACES:
        normals = np.empty(nv * 3, dtype=np.float32)
        me.vertex_normals.foreach_get("vector", normals)
        normals = normals.reshape(nv, 3) @ to_world
        normals /= np.maximum(np.linalg.norm(normals, axis=1), 1e-30)[:, None]
        if me.attributes.get(".hide_vert") is not None:
            keep = ~read_attr(me, ".hide_vert", nv, bool, False)
            co, normals = co[keep], normals[keep]
        return ('VERTS', co, normals)
    starts, totals, cv = face_vertex_arrays(me)
    lp = co[cv]
    centers = np.add.reduceat(lp, starts, axis=0) / totals[:, None].astype(np.float32)
    lp -= np.repeat(centers, totals, axis=0)
    radius = np.sqrt(np.maximum.reduceat((lp * lp).sum(axis=1), starts))
    normals = np.empty(nf * 3, dtype=np.float32)
    me.polygon_normals.foreach_get("vector", normals)
    normals = normals.reshape(nf, 3) @ to_world
    normals /= np.maximum(np.linalg.norm(normals, axis=1), 1e-30)[:, None]
    keep = ~read_attr(me, ".hide_poly", nf, bool, False)
    return ('FACES', centers[keep], radius[keep], normals[keep])


def surface_normal_at(cache, p, r, eye):
    """Нормаль в точке p (мир): средняя по граням (вершинам), которые задевают круг радиуса r вокруг p, лежат в его
    плоскости (|n·(p − c)| ≤ r/2) и смотрят к камере (eye — единичный вектор к ней). None — таких нет."""
    import numpy as np
    P = np.array(p, dtype=np.float32)
    if cache[0] == 'VERTS':
        co, normals = cache[1], cache[2]
        d = co - P
        d2 = (d * d).sum(axis=1)
        idx = np.nonzero(d2 <= r * r)[0]
        if not len(idx):                # сильно приближено: вершин в круге нет — ближайшие
            if not len(d2):
                return None
            r = math.sqrt(float(d2.min())) * 1.5 + r
            idx = np.nonzero(d2 <= r * r)[0]
    else:
        centers, radius, normals = cache[1], cache[2], cache[3]
        d = centers - P
        idx = np.nonzero((d * d).sum(axis=1) <= (radius + r) ** 2)[0]
    if not len(idx):
        return None
    n = normals[idx]
    facing = n @ np.array(eye, dtype=np.float32) > 0.0
    plane = np.abs((n * d[idx]).sum(axis=1))
    ok = facing & (plane <= r * 0.5)
    if not ok.any():
        if not facing.any():
            return None
        return Vector(n[int(np.argmin(np.where(facing, plane, np.inf)))].tolist()).normalized()
    s = n[ok].sum(axis=0)
    length = float(np.linalg.norm(s))
    return Vector((s / length).tolist()) if length > 1e-12 else None


def toward_eye(rv, p):
    if rv.is_perspective:
        return (rv.view_matrix.inverted().translation - p).normalized()
    return rv.view_rotation @ Vector((0.0, 0.0, 1.0))


def geom_normal(context):
    """Нормаль грани под пером штатным привязыванием 3D-курсора — когда позиции меша не те, что на экране
    (Dyntopo, Multires, модификаторы, Shape Keys)."""
    cur = context.scene.cursor
    old = cur.matrix.copy()
    try:
        bpy.ops.view3d.cursor3d('INVOKE_DEFAULT', use_depth=True, orientation='GEOM')
        return cur.matrix.to_3x3().col[2].normalized()
    except RuntimeError:
        return None
    finally:
        cur.matrix = old


def align_gizmo_to_normal(context, normal):
    """Ось Z гизмо — по нормали; X и Y — кратчайшим поворотом от нынешних осей (без закрутки вокруг нормали)."""
    M = orientation_matrix(context)
    q = M.col[2].normalized().rotation_difference(normal.normalized())
    matrix = (q.to_matrix() @ M).to_quaternion().to_matrix()
    custom = context.scene.transform_orientation_slots[0].custom_orientation
    if custom is not None and custom.name == GIZMO_ORIENT and same_gizmo_matrix(custom.matrix, matrix):
        return
    if ensure_gizmo_orientation(context, matrix) is not None:
        _pivot.pop('auto_orient', None)     # оси поставлены намеренно: не «автоматические» оси поворота


def gizmo_rotation_delta(context, op, view_axes=None):
    p = op.properties
    if op.bl_idname == 'TRANSFORM_OT_rotate':
        constrained = tuple(p.constraint_axis)
        count = sum(constrained)
        if count == 1:
            index = constrained.index(True)
        elif count == 2:
            index = constrained.index(False)
        else:
            index = 'XYZ'.index(p.orient_axis)
        axis = Matrix(p.orient_matrix).col[index].normalized()
        if count == 0:
            axis.negate()  # native viewport unconstrained rotation flips axis
        return Matrix.Rotation(p.value, 3, axis)
    if op.bl_idname == 'TRANSFORM_OT_trackball':
        if view_axes is None:
            inverse = context.region_data.perspective_matrix.inverted_safe()
            view_axes = (inverse.col[0].xyz.normalized(), inverse.col[1].xyz.normalized())
        axis = view_axes[0] * p.value[0] + view_axes[1] * p.value[1]
        angle = axis.length
        return Matrix.Identity(3) if angle < 1e-12 else Matrix.Rotation(angle, 3, axis / angle)
    return None


def same_gizmo_matrix(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(3) for j in range(3)) < 1e-5


def apply_gizmo_rotation(context, delta, base=None):
    """Call outside draw, e.g. one-shot completion timer; never changes mesh or pushes undo."""
    base = orientation_matrix(context) if base is None else base
    if not same_gizmo_matrix(orientation_matrix(context), base):
        return False  # another deliberate orientation edit won the race
    matrix = (delta @ base).to_quaternion().to_matrix()
    custom = ensure_gizmo_orientation(context, matrix)
    if custom is None:
        return False
    _pivot['auto_orient'] = matrix.copy()
    return True


def reset_auto_gizmo_orientation(context):
    """Conservative undo/redo fallback: reset only our still-owned automatic matrix."""
    _pivot['orient_epoch'] = _pivot.get('orient_epoch', 0) + 1
    matrix = _pivot.pop('auto_orient', None)
    if matrix is None:
        return False
    slot = context.scene.transform_orientation_slots[0]
    custom = slot.custom_orientation
    if custom is not None and custom.name == GIZMO_ORIENT and same_gizmo_matrix(custom.matrix, matrix):
        slot.type = 'GLOBAL'
        return True
    return False


def queue_gizmo_orientation_reset(context):
    """New object/session detected in draw: invalidate now, change Scene outside draw."""
    _pivot['orient_epoch'] = _pivot.get('orient_epoch', 0) + 1
    matrix = _pivot.pop('auto_orient', None)
    _pivot.pop('rot_view', None)
    if matrix is None:
        return
    scene = context.scene
    def finish():
        if _pivot.get("follow_shutdown", False):
            return None
        try:
            slot = scene.transform_orientation_slots[0]
            custom = slot.custom_orientation
            if custom is not None and custom.name == GIZMO_ORIENT and same_gizmo_matrix(custom.matrix, matrix):
                slot.type = 'GLOBAL'
        except (ReferenceError, RuntimeError, TypeError, AttributeError) as error:
            print('Sculpt Fund: gizmo orientation reset:', error)
        return None
    bpy.app.timers.register(finish, first_interval=0.0)


def capture_gizmo_rotation_view(context, op):
    """Called by existing modal-transform check in draw; only small Python math, no RNA writes."""
    if op.bl_idname != 'TRANSFORM_OT_trackball':
        return
    pointer = op.as_pointer()
    cached = _pivot.get('rot_view')
    if cached is None or cached[0] != pointer:
        inverse = context.region_data.perspective_matrix.inverted_safe()
        _pivot['rot_view'] = (pointer, (inverse.col[0].xyz.normalized(), inverse.col[1].xyz.normalized()))


def queue_gizmo_rotation(context, op):
    cached = _pivot.pop('rot_view', None)
    view_axes = cached[1] if cached is not None and cached[0] == op.as_pointer() else None
    delta = gizmo_rotation_delta(context, op, view_axes)
    if delta is None:
        return
    obj = context.active_object
    key = pivot_key(obj)
    epoch = _pivot.get('orient_epoch', 0)
    base = orientation_matrix(context)
    window, area, region = context.window, context.area, context.region
    def finish():
        if _pivot.get("follow_shutdown", False) or not prefs().controls_on:
            return None
        try:
            with bpy.context.temp_override(window=window, area=area, region=region):
                current = bpy.context.active_object
                if current is not None and pivot_key(current) == key and bpy.context.mode == 'SCULPT' \
                        and _pivot.get('orient_epoch', 0) == epoch:
                    if apply_gizmo_rotation(bpy.context, delta, base):
                        remember_orientation(bpy.context, current)
                    area.tag_redraw()
        except (ReferenceError, RuntimeError, TypeError, AttributeError) as error:
            print('Sculpt Fund: gizmo rotation:', error)
        return None
    bpy.app.timers.register(finish, first_interval=0.0)


# Blender не хранит оси гизмо в истории. Аддон запоминает их для состояния меша (отпечаток позиций вершин): при
# нажатии на ручку гизмо, после поворота кольцом, после поворота осей Alt'ом и «осей по миру». После Ctrl+Z /
# Ctrl+Shift+Z — оси того состояния, к которому вернулась история; незнакомое состояние — оси не трогаются.
_orient_hist = {}
ORIENT_HIST_MAX = 512


def geometry_digest(obj):
    if not mesh_readable(obj):
        return None
    import hashlib
    import numpy as np
    me = obj.data
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    me.attributes["position"].data.foreach_get("vector", co)
    return (obj.name, n, hashlib.blake2b(co.tobytes(), digest_size=16).digest())


def orientation_state(context):
    slot = context.scene.transform_orientation_slots[0]
    custom = slot.custom_orientation
    if custom is not None and custom.name == GIZMO_ORIENT:
        return ('CUSTOM', custom.matrix.copy())
    return (slot.type, None)


def remember_orientation(context, obj=None):
    """Никогда не мешает действию, из которого вызвана (нажатие на ручку и т. п.)."""
    try:
        obj = context.active_object if obj is None else obj
        key = geometry_digest(obj)
        if key is None:
            return
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        return
    _orient_hist.pop(key, None)
    _orient_hist[key] = orientation_state(context)
    while len(_orient_hist) > ORIENT_HIST_MAX:
        _orient_hist.pop(next(iter(_orient_hist)))


def _restore_orientation():
    """Таймер после Ctrl+Z / Ctrl+Shift+Z: оси гизмо того состояния меша, к которому вернулась история."""
    try:
        ov = view3d_override()
        if ov is None or prefs() is _Defaults or not prefs().controls_on or _pivot.get("follow_shutdown", False):
            return None
        with bpy.context.temp_override(**ov):
            ctx = bpy.context
            obj = ctx.active_object
            if ctx.mode != 'SCULPT' or obj is None:
                return None
            state = _orient_hist.get(geometry_digest(obj))
            if state is None:
                return None
            kind, matrix = state
            if kind == 'CUSTOM':
                if ensure_gizmo_orientation(ctx, matrix) is not None:
                    _pivot['auto_orient'] = matrix.copy()
            else:
                _pivot.pop('auto_orient', None)
                slot = ctx.scene.transform_orientation_slots[0]
                if slot.type != kind:
                    slot.type = kind
            ov["area"].tag_redraw()
    except (ReferenceError, RuntimeError, TypeError, AttributeError) as error:
        print("Sculpt Fund: gizmo orientation from history:", error)
    return None


# --- навигация и жесты по пустому месту -----------------------------------------------------------------

class SCULPTFUND_OT_canvas(bpy.types.Operator):
    """Жесты ZBrush по пустому месту: вращение, сдвиг, зум, крен; маска и ремеш с Ctrl; Alt+клик = другой объект"""
    bl_idname = "sculpt_fund.canvas"
    bl_label = "ZBrush Canvas Gesture"
    bl_options = {'BLOCKING'}

    button: StringProperty(default='LEFTMOUSE')
    anywhere: BoolProperty(default=False, description="Навигация правой кнопкой: работает и над мешем")
    from_tool: BoolProperty(default=False, description="Строка раскладки инструмента Transform (режим W)")
    grab_check: BoolProperty(default=False, description="Строка перед мазком: кисть с Projected (Grab) по пустому фону")

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and context.area and context.area.type == 'VIEW_3D' and context.region_data

    def invoke(self, context, event):
        # Сюда событие доходит, только если мазок кисти его пропустил (Ignore Background Click): под пером нет меша.
        # Проверка «меш или фон» делается самим Blender, без Python, поэтому обычный скульпт не нагружается.
        if getattr(self, "grab_check", False):
            # Grab (Projected) цепляет меш радиусом и мимо него, поэтому Blender не считает фон фоном. С навигацией ЛКМ:
            # под пером ничего нет — навигация; под пером другой меш (или этот) — мазок, Grab тянет радиусом (22.10.2026)
            brush = context.tool_settings.sculpt.brush
            if (not brush_tool_active(context) or brush is None or brush.falloff_shape != 'PROJECTED'
                    or depth_hit(context, event)):
                return {'PASS_THROUGH'}
        if self.from_tool:
            # Режим гизмо: строка стоит раньше «протяжки откуда угодно» инструмента (Move / Transform …). По мешу —
            # штатное перемещение, Alt — центр гизмо по поверхности; по фону — навигация, как с кистью.
            if not gizmo_tool_active(context):
                return {'PASS_THROUGH'}
            if prefs().disable_lmb_navigation and event.value == 'CLICK_DRAG':
                # Active-mesh Alt pivot drag is already handled from PRESS.
                # The separate Generic Gizmo handler normally consumes handle
                # drags first. This guard consumes background-started drags,
                # even when the pointer has subsequently crossed the mesh.
                if xform_gizmo_hit(context)[1] is not None:
                    return {'PASS_THROUGH'}
                return {'CANCELLED'}
            if gizmo_pressed(event):
                return {'PASS_THROUGH'}
            obj = context.active_object
            if obj is not None and depth_hit(context, event, obj):
                if alt_held(event) and not event.ctrl and not event.shift:
                    return self.start_pivot_drag(context, event, obj)
                return {'PASS_THROUGH'}
        elif not self.anywhere and not brush_tool_active(context):
            return {'PASS_THROUGH'}
        self.ctrl, self.alt, self.shift = event.ctrl, event.alt, event.shift
        if prefs().disable_lmb_navigation and not self.anywhere:
            # No camera modal handler. Alt PRESS must remain unhandled so
            # Blender can synthesize the distinct Alt CLICK command.
            return {'PASS_THROUGH'} if self.from_tool and self.alt else {'CANCELLED'}
        if self.anywhere:
            self.mode = 'ZOOM' if self.ctrl else ('PAN' if self.alt else 'ORBIT')
        elif self.alt:
            self.mode = 'PAN'
        else:
            self.mode = 'ORBIT'
        self.shift_at_start = self.shift
        if self.mode == 'ORBIT' and not self.shift:
            # Вращение — штатное, как на СКМ: плавное, с настройками Navigation, курсор прячется на время вращения.
            # Своё вращение на Python держало кружок кисти на месте нажатия («кисточка прилипает к экрану»)
            if safe(bpy.ops.view3d.rotate, 'INVOKE_DEFAULT') != {'CANCELLED'}:
                return {'FINISHED'}
        self.start = (event.mouse_region_x, event.mouse_region_y)
        self.last = self.start
        self.moved = False
        self.free_rot = context.region_data.view_rotation.copy()
        thr = context.preferences.inputs.drag_threshold_tablet if event.is_tablet else context.preferences.inputs.drag_threshold_mouse
        self.threshold = max(3, thr)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    # навигация
    def orbit(self, context, dx, dy, snap):
        rv = context.region_data
        inputs = context.preferences.inputs
        q = self.free_rot
        if inputs.view_rotate_method == 'TRACKBALL':
            length = math.hypot(dx, dy)
            if length:
                size = min(context.region.width, context.region.height) or 1
                angle = length / size * math.pi * inputs.view_rotate_sensitivity_trackball
                axis = (q @ Vector((-dy, dx, 0.0))).normalized()
                q = Quaternion(axis, -angle) @ q
        else:
            s = inputs.view_rotate_sensitivity_turntable
            q = Quaternion((0, 0, 1), -dx * s) @ q
            q = Quaternion(q @ Vector((1, 0, 0)), dy * s) @ q
        q.normalize()
        self.free_rot = q
        new = snap_quat(q) if snap else q
        old = rv.view_rotation.copy()
        # Setting view_rotation through RNA marks the view as USER, so native
        # is_orthographic_side_view alone cannot recognize our previous snap.
        was_axis_aligned = abs(old.dot(snap_quat(old))) > 1.0 - 1e-6
        if inputs.use_rotate_around_active and context.active_object:
            obj = context.active_object
            pivot = obj.matrix_world @ (sum((Vector(c) for c in obj.bound_box), Vector()) / 8)
            delta = new @ old.inverted()
            rv.view_location = pivot + delta @ (rv.view_location - pivot)
        rv.view_rotation = new
        if inputs.use_auto_perspective:
            if snap:
                rv.view_perspective = 'ORTHO'
            elif rv.view_perspective == 'ORTHO' and was_axis_aligned:
                rv.view_perspective = 'PERSP'

    def pan(self, context, prev, cur):
        rv, region = context.region_data, context.region
        a = view3d_utils.region_2d_to_location_3d(region, rv, prev, rv.view_location)
        b = view3d_utils.region_2d_to_location_3d(region, rv, cur, rv.view_location)
        rv.view_location += a - b

    def zoom(self, context, dx, dy):
        rv = context.region_data
        d = dy + dx * 0.25
        if self.ctrl:
            d = -d      # Ctrl-зум (Ctrl+СКМ / Ctrl+ПКМ) инвертирован по просьбе пользователя: вверх — отдалить
        rv.view_distance = max(1e-4, rv.view_distance * math.exp(-d * 0.006))

    def roll(self, context, dx):
        rv = context.region_data
        q = rv.view_rotation
        axis = q @ Vector((0, 0, 1))
        rv.view_rotation = (Quaternion(axis, dx * context.preferences.inputs.view_rotate_sensitivity_turntable) @ q).normalized()
        self.free_rot = rv.view_rotation.copy()

    def finish_click(self, context, event):
        # Другой объект — только двойным Alt+кликом (alt_select). Одиночный Alt+клик по пустому месту в режиме W —
        # центр гизмо в центр незамаскированного
        if self.alt and not self.ctrl and not self.anywhere and self.from_tool and not depth_hit(context, event):
            set_pivot_unmasked(context)

    # режим W: Alt+клик / протяжка по мешу — центр гизмо в точку под пером, оси — по нормали поверхности
    def start_pivot_drag(self, context, event, obj):
        self.mode = 'PIVOT'
        self.pivot_obj = obj
        self.surface = None         # грани для нормали — при первом попадании, один раз на протяжку
        _pivot["busy"] = True
        self.move_pivot(context, event)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def move_pivot(self, context, event):
        obj = self.pivot_obj
        p = depth_point(context, event, obj)
        if p is None:
            return      # мимо меша: центр остаётся в последней точке на поверхности (как у Blender)
        safe(bpy.ops.sculpt.set_pivot_position, mode='SURFACE',
             mouse_x=event.mouse_region_x, mouse_y=event.mouse_region_y)
        pivot_store(obj, obj.matrix_world.inverted_safe() @ p)
        n = self.surface_normal(context, obj, p)
        if n is not None:
            align_gizmo_to_normal(context, n)

    def surface_normal(self, context, obj, p):
        if not mesh_readable(obj) or obj.data.shape_keys or any(m.show_viewport for m in obj.modifiers):
            return geom_normal(context)
        if self.surface is None:
            self.surface = surface_cache(obj)
            if self.surface is None:
                return None
        region, rv = context.region, context.region_data
        c = view3d_utils.location_3d_to_region_2d(region, rv, p)
        if c is None:
            return None
        px = SURFACE_NORMAL_PX * context.preferences.system.ui_scale
        r = (view3d_utils.region_2d_to_location_3d(region, rv, (c.x + px, c.y), p) - p).length
        return surface_normal_at(self.surface, p, max(r, 1e-9), toward_eye(rv, p))

    def modal(self, context, event):
        if getattr(self, "mode", None) == 'PIVOT':
            if event.type == 'MOUSEMOVE':
                self.move_pivot(context, event)
            elif (event.type == self.button and event.value == 'RELEASE') or event.type == 'ESC':
                _pivot["busy"] = False
                self.surface = None
                remember_orientation(context, self.pivot_obj)      # оси по нормали — для этого состояния меша
                context.area.tag_redraw()
                return {'FINISHED'}
            return {'RUNNING_MODAL'}
        if event.type == 'MOUSEMOVE':
            cur = (event.mouse_region_x, event.mouse_region_y)
            if not self.moved and math.hypot(cur[0] - self.start[0], cur[1] - self.start[1]) >= self.threshold:
                self.moved = True
                if self.mode == 'ORBIT' and not self.anywhere and self.shift_at_start and not event.shift:
                    self.mode = 'ROLL'
            if self.moved:
                dx, dy = cur[0] - self.last[0], cur[1] - self.last[1]
                if self.mode == 'ORBIT':
                    self.orbit(context, dx, dy, snap=event.shift)
                elif self.mode == 'PAN':
                    self.pan(context, self.last, cur)
                elif self.mode == 'ZOOM':
                    self.zoom(context, dx, dy)
                elif self.mode == 'ROLL':
                    self.roll(context, dx)
            self.last = cur
            return {'RUNNING_MODAL'}
        if event.type in {'LEFT_ALT', 'RIGHT_ALT'} and not self.anywhere:
            if event.value == 'RELEASE' and self.mode == 'PAN':
                self.mode = 'ZOOM'      # ZBrush: Alt+клик, отпустить Alt, тянуть = масштаб
            elif event.value == 'PRESS' and self.mode == 'ZOOM' and not self.ctrl:
                self.mode = 'PAN'
            return {'RUNNING_MODAL'}
        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'}:
            if self.mode == 'ORBIT' and self.moved:
                self.orbit(context, 0, 0, snap=event.value == 'PRESS')
                context.area.tag_redraw()
            if event.value == 'RELEASE' and self.mode == 'ORBIT' and not self.anywhere and self.shift_at_start and not self.moved:
                self.mode = 'ROLL'      # ZBrush: Shift, клик, отпустить Shift, тянуть = крен
            return {'RUNNING_MODAL'}
        if event.type == self.button and event.value == 'RELEASE':
            if not self.moved:
                self.finish_click(context, event)
            return {'FINISHED'}
        if event.type == 'ESC':
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


class SCULPTFUND_OT_alt_select(bpy.types.Operator):
    """Быстрый двойной Alt+клик по другому объекту — перейти на него в том же режиме (как сабтул в ZBrush)"""
    bl_idname = "sculpt_fund.alt_select"
    bl_label = "Выбрать sculpt-объект"

    from_tool: BoolProperty(default=False, options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return (context.mode == 'SCULPT' and context.area and context.area.type == 'VIEW_3D'
                and context.region_data and prefs().controls_on)

    def invoke(self, context, event):
        if not alt_held(event):
            return {'PASS_THROUGH'}         # Blender «помнит» отпущенный Alt: не переключать объект
        # The tool map runs before Sculpt. Do not pick twice if it passed on an
        # active-mesh stroke/pivot. A highlighted transform handle owns Alt.
        if self.from_tool:
            if not gizmo_tool_active(context) or gizmo_pressed(event):
                return {'PASS_THROUGH'}
        elif gizmo_tool_active(context):
            return {'PASS_THROUGH'}
        # Native GPU object picking resolves the frontmost object's identity.
        # Do not gate this by cursor depth or the active object's bounding box:
        # overlapping bounds are common for sculpt parts. CANCELLED on the
        # current object passes PRESS to the native inverse brush/pivot.
        result = safe(bpy.ops.object.transfer_mode, 'INVOKE_DEFAULT', True)
        return {'FINISHED'} if result == {'FINISHED'} else {'PASS_THROUGH'}


class SCULPTFUND_OT_alt_click(bpy.types.Operator):
    """Alt+клик по пустому месту в режиме гизмо — центр гизмо в центр незамаскированного (объект не переключает:
    это двойной Alt+клик)"""
    bl_idname = "sculpt_fund.alt_click"
    bl_label = "Alt+клик по фону"

    @classmethod
    def poll(cls, context):
        return (context.mode == 'SCULPT' and context.area and context.area.type == 'VIEW_3D'
                and context.region_data and prefs().controls_on)

    def invoke(self, context, event):
        if not alt_held(event):
            return {'PASS_THROUGH'}
        if gizmo_tool_active(context) and not depth_hit(context, event):
            set_pivot_unmasked(context, report=self.report)
        return {'FINISHED'}     # клик поглощается: штатный Alt+клик Blender открыл бы меню выбора объекта


class SCULPTFUND_OT_mask_click(bpy.types.Operator):
    """Ctrl+клик по мешу = блюр маски, Ctrl+Alt+клик = шарп (на всю маску, как в ZBrush)"""
    bl_idname = "sculpt_fund.mask_click"
    bl_label = "Mask Blur / Sharpen"
    # Без 'UNDO', а штатные операторы внутри вызываются с undo=True: каждый пишет свой полноценный шаг истории, как
    # нажатый руками. Внутри UNDO-оператора Blender сливает шаги скульпта в один, и при нескольких операторах подряд
    # Ctrl+Z восстанавливает не то; вызов из Python без undo=True шаг не пишет вовсе (тест t21, 20.10.2026).
    bl_options = {'REGISTER'}

    filter_type: EnumProperty(items=(('SMOOTH', "Blur", ""), ('SHARPEN', "Sharpen", "")))

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT'

    def invoke(self, context, event):
        w_mode = gizmo_tool_active(context)
        if not w_mode and not brush_tool_active(context):
            return {'PASS_THROUGH'}
        if w_mode and self.filter_type == 'SMOOTH':
            res = mask_all_but_face_set(context, event, self.report)      # режим W: маска по полигруппе
            if res is not None:
                return res
        elif depth_hit(context, event, context.active_object):
            return self.execute(context)
        if self.filter_type == 'SMOOTH' and prefs().use_canvas_masking:
            return safe(bpy.ops.paint.mask_flood_fill, 'EXEC_DEFAULT', True, mode='INVERT', report=self.report)
        return {'CANCELLED'}

    def execute(self, context):
        return safe(bpy.ops.sculpt.mask_filter, 'EXEC_DEFAULT', True, filter_type=self.filter_type, report=self.report)


def _gesture_has_vertices(obj, region_size, persp, props, kind):
    """Попала ли в рамку / лассо хоть одна видимая вершина. numpy; на больших мешах сначала выборка."""
    import numpy as np
    me = obj.data
    n = len(me.vertices)
    if n == 0:
        return False
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    hv = me.attributes.get(".hide_vert")
    if hv is not None and len(hv.data) == n:
        hidden = np.zeros(n, dtype=bool)
        hv.data.foreach_get("value", hidden)
        co = co[~hidden]
    if len(co) == 0:
        return False
    m = np.array(persp @ obj.matrix_world, dtype=np.float64)
    pts = np.c_[co, np.ones(len(co))] @ m.T
    w = pts[:, 3]
    front = w > 1e-9
    w = np.where(front, w, 1.0)
    px = (pts[:, 0] / w + 1.0) * 0.5 * region_size[0]
    py = (pts[:, 1] / w + 1.0) * 0.5 * region_size[1]
    if kind == 'BOX':
        inside = front & (px >= props["xmin"]) & (px <= props["xmax"]) & (py >= props["ymin"]) & (py <= props["ymax"])
        return bool(inside.any())
    poly = np.array(props["path"], dtype=np.float64)
    if len(poly) < 3:
        return False
    x0, y0 = poly.min(axis=0)
    x1, y1 = poly.max(axis=0)
    cand = front & (px >= x0) & (px <= x1) & (py >= y0) & (py <= y1)
    idx = np.nonzero(cand)[0]
    if len(idx) == 0:
        return False

    def any_inside(sel):
        qx, qy = px[sel], py[sel]
        inside = np.zeros(len(sel), dtype=bool)
        xj, yj = poly[-1]
        for xi, yi in poly:
            if yi != yj:
                cross = ((yi > qy) != (yj > qy)) & (qx < (xj - xi) * (qy - yi) / (yj - yi) + xi)
                inside ^= cross
            xj, yj = xi, yi
        return bool(inside.any())
    if len(idx) > 4000:
        step = max(1, len(idx) // 4000)
        if any_inside(idx[::step]):
            return True
    return any_inside(idx)


# --- жесты рамкой / лассо (Ctrl, Ctrl+Shift) ---------------------------------------------------------------
# Своя рамка / лассо вместо штатных: в центре рамки крестик (мерить пропорции, как в ZBrush), Space двигает рамку,
# Alt во время протяжки переключает «маска / стереть» и «оставить / скрыть». Пустота проверяется сразу при
# отпускании пера, а штатный оператор вызывается только для непустой фигуры — одним шагом истории.

_gesture_handles = set()        # обработчики рисования жестов (снимаются при выключении аддона, если что-то осталось)

SHAPE_OF = {'MASK_BOX': 'BOX', 'MASK_LASSO': 'LASSO', 'MASK_LINE': 'LINE', 'SELECT_BOX': 'BOX', 'TRIM_BOX': 'BOX',
            'SELECT_LASSO': 'LASSO', 'TRIM_LASSO': 'LASSO'}


def _draw_gesture(op):
    try:
        if bpy.context.region != op.region:
            return
        import gpu
        from gpu_extras.batch import batch_for_shader
        ui = bpy.context.preferences.system.ui_scale
        segs = []
        if op.shape == 'BOX':
            (x0, y0), (x1, y1) = op.rect()
            c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            for i in range(4):
                segs += [c[i - 1], c[i]]
            cx, cy, s = (x0 + x1) / 2, (y0 + y1) / 2, 9 * ui      # крестик в центре рамки
            segs += [(cx - s, cy), (cx + s, cy), (cx, cy - s), (cx, cy + s)]
        else:
            p = op.path + [tuple(op.cur)]
            for i in range(len(p)):
                segs += [p[i - 1], p[i]]
        if len(segs) < 2:
            return
        pos = [(x, y, 0.0) for x, y in segs]
        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("viewportSize", (op.region.width, op.region.height))
        batch = batch_for_shader(shader, 'LINES', {"pos": pos})
        for width, color in ((3.5 * ui, (0.0, 0.0, 0.0, 0.55)), (1.5 * ui, op.color())):
            shader.uniform_float("lineWidth", width)
            shader.uniform_float("color", color)
            batch.draw(shader)
        gpu.state.blend_set('NONE')
    except (ReferenceError, AttributeError):
        pass


def path_items(path):
    return [{"name": "", "loc": (float(x), float(y)), "time": 0.0} for x, y in path]


class SCULPTFUND_OT_gesture(bpy.types.Operator):
    """Ctrl / Ctrl+Shift+протяжка: рамка (с крестиком в центре) или лассо. Пустая фигура: маска — сброс маски, а без
    маски — DynaMesh; Ctrl+Shift — инверсия видимости"""
    bl_idname = "sculpt_fund.gesture"
    bl_label = "ZBrush Mask / Visibility Gesture"

    target: EnumProperty(items=(('MASK', "Mask", "Ctrl"), ('CS', "Ctrl+Shift", "Ctrl+Shift")))
    on_mesh: BoolProperty(default=False, description="Строка до кисти маски: Mask Lasso рисуется лассо и по мешу")

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and context.region_data is not None

    def invoke(self, context, event):
        if not (brush_tool_active(context) or gizmo_tool_active(context)):
            return {'PASS_THROUGH'}         # другие инструменты (маска рамкой с панели и т.п.) — как в Blender
        self.tool = prefs().ctrl_bg_tool if self.target == 'MASK' else prefs().cs_tool
        self.shape = SHAPE_OF.get(self.tool, 'LINE')
        if self.on_mesh and self.shape != 'LASSO':
            return {'PASS_THROUGH'}         # Mask Box / Line: по мешу — кисть маски (как в ZBrush), с фона — фигура
        self.alt = bool(event.alt)
        if self.shape == 'LINE':
            return self.run_line(context)
        self.region = context.region
        px = getattr(event, "mouse_prev_press_x", event.mouse_x) - context.region.x
        py = getattr(event, "mouse_prev_press_y", event.mouse_y) - context.region.y
        self.start = [px, py]
        self.cur = [event.mouse_region_x, event.mouse_region_y]
        self.path = [(px, py)]
        self.last = tuple(self.cur)
        self.space = False
        self._handle = bpy.types.SpaceView3D.draw_handler_add(_draw_gesture, (self,), 'WINDOW', 'POST_PIXEL')
        _gesture_handles.add(self._handle)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def run_line(self, context):
        if self.target == 'MASK':
            safe(bpy.ops.paint.mask_line_gesture, 'INVOKE_DEFAULT', True, mode='VALUE',
                 value=0.0 if self.alt else 1.0, report=self.report)
        else:
            module, name = CS_OPS[self.tool].split('.')
            safe(getattr(getattr(bpy.ops, module), name), 'INVOKE_DEFAULT', True, report=self.report)
        return {'FINISHED'}

    def rect(self):
        (ax, ay), (bx, by) = self.start, self.cur
        return (min(ax, bx), min(ay, by)), (max(ax, bx), max(ay, by))

    def color(self):
        if self.alt:
            return (1.0, 0.38, 0.32, 0.95)          # стереть маску / скрыть внутри
        if self.target == 'MASK':
            return (1.0, 1.0, 1.0, 0.95)
        return (1.0, 0.72, 0.3, 0.95) if self.tool.startswith('TRIM') else (0.45, 0.85, 1.0, 0.95)

    def stop_draw(self, context):
        if getattr(self, "_handle", None) is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            _gesture_handles.discard(self._handle)
            self._handle = None
        context.area.tag_redraw()

    def modal(self, context, event):
        try:
            return self._modal(context, event)
        except Exception:
            self.stop_draw(context)
            raise

    def _modal(self, context, event):
        context.area.tag_redraw()
        if event.type == 'MOUSEMOVE':
            x, y = event.mouse_region_x, event.mouse_region_y
            dx, dy = x - self.last[0], y - self.last[1]
            if self.space and self.shape == 'BOX':                 # Space: двигать рамку целиком
                self.start[0] += dx
                self.start[1] += dy
            elif self.space and self.shape == 'LASSO':             # Space: двигать лассо целиком (27.10.2026)
                self.path = [(px + dx, py + dy) for px, py in self.path]
            elif self.shape == 'LASSO' and math.hypot(x - self.path[-1][0], y - self.path[-1][1]) >= 2:
                self.path.append((x, y))
            self.cur = [x, y]
            self.last = (x, y)
        elif event.type in {'LEFT_ALT', 'RIGHT_ALT'}:
            self.alt = event.value != 'RELEASE'
        elif event.type == 'SPACE':
            self.space = event.value != 'RELEASE'
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.stop_draw(context)
            return self.apply(context)
        elif event.type in {'ESC', 'RIGHTMOUSE'}:
            self.stop_draw(context)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def apply(self, context):
        obj = context.active_object
        if self.shape == 'BOX':
            (x0, y0), (x1, y1) = self.rect()
            props = dict(xmin=int(x0), xmax=int(x1), ymin=int(y0), ymax=int(y1))
        else:
            if math.hypot(self.cur[0] - self.path[-1][0], self.cur[1] - self.path[-1][1]) >= 1:
                self.path.append(tuple(self.cur))
            props = {"path": self.path}
        size = (self.region.width, self.region.height)
        empty = obj is None or obj.type != 'MESH' or not _gesture_has_vertices(
            obj, size, context.region_data.perspective_matrix, props, self.shape)
        if self.target == 'MASK':
            if empty:
                return self.empty_mask(context, obj)
            value = 0.0 if self.alt else 1.0
            if self.shape == 'BOX':
                return safe(bpy.ops.paint.mask_box_gesture, 'EXEC_DEFAULT', True, mode='VALUE', value=value,
                            report=self.report, **props)
            return safe(bpy.ops.paint.mask_lasso_gesture, 'EXEC_DEFAULT', True, path=path_items(self.path),
                        mode='VALUE', value=value, report=self.report)
        if empty:                                                    # Ctrl+Shift по пустому месту: инверсия видимости
            if mesh_readable(obj) and not read_attr(obj.data, ".hide_poly", len(obj.data.polygons), bool, False).any():
                return {'CANCELLED'}        # всё видно: инверсия спрятала бы весь меш
            return safe(bpy.ops.paint.visibility_invert, 'EXEC_DEFAULT', True, report=self.report)
        area = 'Inside' if self.alt else 'OUTSIDE'
        if self.tool == 'SELECT_BOX':
            return safe(bpy.ops.paint.hide_show, 'EXEC_DEFAULT', True, action='HIDE', area=area,
                        report=self.report, **props)
        if self.tool == 'SELECT_LASSO':
            return safe(bpy.ops.paint.hide_show_lasso_gesture, 'EXEC_DEFAULT', True, path=path_items(self.path),
                        action='HIDE', area=area, report=self.report)
        if self.tool == 'TRIM_BOX':
            return safe(bpy.ops.sculpt.trim_box_gesture, 'EXEC_DEFAULT', True, report=self.report, **props)
        return safe(bpy.ops.sculpt.trim_lasso_gesture, 'EXEC_DEFAULT', True, path=path_items(self.path),
                    report=self.report)

    def empty_mask(self, context, obj):
        """Пустая рамка, как в ZBrush: есть маска — сброс; маски нет — DynaMesh."""
        if obj is None or not prefs().use_canvas_masking:
            return {'CANCELLED'}
        if has_mask(obj):
            return safe(bpy.ops.paint.mask_flood_fill, 'EXEC_DEFAULT', True, mode='VALUE', value=0.0, report=self.report)
        if not self.alt:        # DynaMesh — всегда, без флажка у объекта (его случайно выключали: «не ремешится»)
            return safe(bpy.ops.sculpt_fund.voxel_remesh, 'EXEC_DEFAULT', report=self.report)
        return {'CANCELLED'}


class SCULPTFUND_OT_set_ctrl_tool(bpy.types.Operator):
    """Выбрать, что тянется Ctrl+протяжкой с пустого места (по мешу — всегда кисть маски)"""
    bl_idname = "sculpt_fund.set_ctrl_tool"
    bl_label = "Set Ctrl Mask Tool"
    tool: EnumProperty(items=[(t[0], t[1], t[2]) for t in CTRL_TOOLS])

    def execute(self, context):
        prefs().ctrl_bg_tool = self.tool
        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


class SCULPTFUND_OT_cs_click(bpy.types.Operator):
    """Ctrl+Shift+клик: по фону — показать всё; по Face Set — изолировать, повторно — скрыть его"""
    bl_idname = "sculpt_fund.cs_click"
    bl_label = "Ctrl+Shift Click (Visibility)"
    bl_options = {'REGISTER'}       # шаг истории пишет штатный оператор внутри (см. mask_click)

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and context.region_data

    def invoke(self, context, event):
        obj = context.active_object
        if not depth_hit(context, event, obj):
            return safe(bpy.ops.paint.hide_show_all, 'EXEC_DEFAULT', True, action='SHOW', report=self.report)  # фон: показать всё
        if gizmo_tool_active(context):                              # режим W: как Ctrl+клик — маска по полигруппе
            return mask_all_but_face_set(context, event, self.report) or {'CANCELLED'}
        fsv = bpy.ops.sculpt.face_set_change_visibility
        info = None if obj.modifiers else visible_face_sets(obj)
        if info is None:
            return safe(fsv, 'INVOKE_DEFAULT', True, mode='TOGGLE', report=self.report)
        any_hidden, sets = info
        if not any_hidden:
            return safe(fsv, 'INVOKE_DEFAULT', True, mode='TOGGLE', report=self.report)          # изолировать группу
        if len(sets) == 1:
            return safe(bpy.ops.paint.visibility_invert, 'EXEC_DEFAULT', True, report=self.report)  # видна одна — скрыть
        return safe(fsv, 'INVOKE_DEFAULT', True, mode='HIDE_ACTIVE', report=self.report)          # скрыть группу под пером


class SCULPTFUND_OT_set_cs_tool(bpy.types.Operator):
    """Выбрать инструмент для Ctrl+Shift+протяжки"""
    bl_idname = "sculpt_fund.set_cs_tool"
    bl_label = "Set Ctrl+Shift Tool"
    tool: EnumProperty(items=[(t[0], t[1], t[2]) for t in CS_TOOLS])

    def execute(self, context):
        prefs().cs_tool = self.tool
        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


# Shift+F (Polyframe): цвета полигрупп; сетка — по галочке «Shift+F: сетка» и только у активного объекта
# (Object.show_wire). Общая сетка оверлея (show_wireframes) рисует все объекты сцены — её Polyframe не включает.
# Цвета Face Sets Blender и так рисует только у объекта в Sculpt Mode (он один — активный).
_poly_wire = {}     # имя объекта → его show_wire до Polyframe; сетку объекту ставит только Polyframe
_poly_last = None


def polyframe_targets():
    """Имена объектов, которым нужна сетка Polyframe: активный в Sculpt, если в его окне показаны Face Sets."""
    p = prefs()
    if not (p.controls_on and getattr(p, "polyframe_wire", False)):
        return set()
    names = set()
    for win in bpy.context.window_manager.windows:
        obj = win.view_layer.objects.active
        if obj is None or obj.type != 'MESH' or obj.mode != 'SCULPT':
            continue
        if any(a.type == 'VIEW_3D' and a.spaces.active.overlay.show_sculpt_face_sets for a in win.screen.areas):
            names.add(obj.name)
    return names


def polyframe_signature():
    p = prefs()
    return (p.controls_on, getattr(p, "polyframe_wire", False), tuple(
        (w.view_layer.objects.active.as_pointer() if w.view_layer.objects.active else 0,
         w.view_layer.objects.active.mode if w.view_layer.objects.active else 'OBJECT',
         any(a.type == 'VIEW_3D' and a.spaces.active.overlay.show_sculpt_face_sets for a in w.screen.areas))
        for w in bpy.context.window_manager.windows))


def set_polyframe_wires(on):
    """Сетка Polyframe: on=False — объектам их собственная настройка (перед сохранением файла), True — снова сетка."""
    for name, original in list(_poly_wire.items()):
        obj = bpy.data.objects.get(name)
        if obj is not None:
            obj.show_wire = True if on else original


def sync_polyframe():
    """Сетка Polyframe только у нужных объектов (polyframe_targets), у остальных — как было до неё."""
    global _poly_last
    if _pivot.get("follow_shutdown", False):
        return None
    try:
        want = polyframe_targets()
        for name in [n for n in _poly_wire if n not in want]:
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.show_wire = _poly_wire[name]
            del _poly_wire[name]
        for name in want:
            obj = bpy.data.objects[name]
            _poly_wire.setdefault(name, obj.show_wire)
            if not obj.show_wire:
                obj.show_wire = True
        _poly_last = polyframe_signature()
    except (ReferenceError, RuntimeError, KeyError, AttributeError) as e:
        _poly_last = None
        print("Sculpt Fund: polyframe:", e)
    return None


def update_polyframe(self, context):
    sync_polyframe()


class SCULPTFUND_OT_polyframe(bpy.types.Operator):
    """Shift+F: цвета полигрупп (Polyframe в ZBrush); сетка активного объекта — галочкой «Shift+F: сетка» в панели N"""
    bl_idname = "sculpt_fund.polyframe"
    bl_label = "Polyframe"

    def execute(self, context):
        if context.space_data is None or context.space_data.type != 'VIEW_3D':
            return {'CANCELLED'}
        ov = context.space_data.overlay
        ov.show_sculpt_face_sets = not ov.show_sculpt_face_sets
        ov.show_wireframes = False      # общая сетка — у всех объектов сцены; сетка Polyframe — только у активного
        sync_polyframe()
        return {'FINISHED'}


class SCULPTFUND_OT_toggle(bpy.types.Operator):
    """Включить или выключить управление ZBrush (обычный Blender — без удаления аддона). Ctrl+Shift+Alt+Z"""
    bl_idname = "sculpt_fund.toggle"
    bl_label = "ZBrush Controls On/Off"

    def execute(self, context):
        p = prefs()
        if p is _Defaults:
            return {'CANCELLED'}
        p.controls_on = not p.controls_on
        self.report({'INFO'}, "Управление ZBrush: " + ("включено" if p.controls_on else "выключено, обычный Blender"))
        return {'FINISHED'}


class SCULPTFUND_OT_frame(bpy.types.Operator):
    """F: показать модель целиком (в Sculpt Mode штатный Frame Selected центрирует на последнем мазке)"""
    bl_idname = "sculpt_fund.frame"
    bl_label = "Frame Model"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.region_data is not None

    def execute(self, context):
        obj = context.active_object
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        lo = Vector((min(p[i] for p in pts) for i in range(3)))
        hi = Vector((max(p[i] for p in pts) for i in range(3)))
        radius = max((hi - lo).length / 2, 1e-4)
        rv, space, region = context.region_data, context.space_data, context.region
        fov = 2 * math.atan(18.0 / max(space.lens, 1.0))
        aspect = region.width / max(region.height, 1)
        if aspect < 1:
            fov = 2 * math.atan(math.tan(fov / 2) * aspect)
        rv.view_location = (lo + hi) / 2
        rv.view_distance = radius / math.sin(fov / 2) * 1.05
        return {'FINISHED'}


def multires(obj):
    return next((m for m in obj.modifiers if m.type == 'MULTIRES'), None)


class SCULPTFUND_OT_subdiv_level(bpy.types.Operator):
    """D / Shift+D: уровень Multires выше / ниже"""
    bl_idname = "sculpt_fund.subdiv_level"
    bl_label = "Subdivision Level"
    bl_options = {'REGISTER', 'UNDO'}
    delta: IntProperty(default=1)

    def execute(self, context):
        m = multires(context.active_object) if context.active_object else None
        if m is None:
            self.report({'INFO'}, "Нет Multires: уровни D / Shift+D — только у меша с Multires")
            return {'CANCELLED'}
        level = max(0, min(m.total_levels, m.sculpt_levels + self.delta))
        m.sculpt_levels = m.levels = level
        return {'FINISHED'}


class SCULPTFUND_OT_divide(bpy.types.Operator):
    """Ctrl+D: подразделить (Divide) уже добавленный Multires. Сам Multires аддон не добавляет"""
    bl_idname = "sculpt_fund.divide"
    bl_label = "Divide"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        m = multires(obj) if obj is not None else None
        if m is None:
            # Multires меняет работу почти всех функций аддона (копия, замена, отделение) — только по решению
            # пользователя, вручную в Modifiers (20.10.2026: «мультирез добавляется, я не просил»)
            self.report({'INFO'}, "Нет Multires: Ctrl+D его не добавляет (добавьте вручную в Modifiers, если нужен)")
            return {'CANCELLED'}
        return safe(bpy.ops.object.multires_subdivide, modifier=m.name, mode='CATMULL_CLARK', report=self.report)


class SCULPTFUND_OT_group_masked(bpy.types.Operator):
    """Ctrl+W: Face Set из маски и сброс маски; маски нет — Face Set из видимого (Group Visible)"""
    bl_idname = "sculpt_fund.group_masked"
    bl_label = "Group Masked"
    bl_options = {'REGISTER'}       # два шага истории от штатных операторов (см. mask_click)

    def execute(self, context):
        obj = context.active_object
        if obj is not None and obj.use_dynamic_topology_sculpting:
            # Полигруппы с Dyntopo Blender не создаёт; раньше отказ уходил только в строку состояния (22.10.2026)
            text = "Ctrl+W: с Dyntopo полигруппы не создаются — выключите Dyntopo или сделайте Remesh"
            self.report({'WARNING'}, text)
            view_message(text, 3.0)
            return {'CANCELLED'}
        if not has_mask(obj):
            return safe(bpy.ops.sculpt.face_sets_create, 'EXEC_DEFAULT', True, mode='VISIBLE', report=self.report)
        if safe(bpy.ops.sculpt.face_sets_create, 'EXEC_DEFAULT', True, mode='MASKED', report=self.report) == {'CANCELLED'}:
            return {'CANCELLED'}
        safe(bpy.ops.paint.mask_flood_fill, 'EXEC_DEFAULT', True, mode='VALUE', value=0.0, report=self.report)
        return {'FINISHED'}


# --- замена примитивом ----------------------------------------------------------------------------------

PRIMITIVES = (
    ('UV_SPHERE', "UV Sphere", 'MESH_UVSPHERE'),
    ('QUAD_SPHERE', "Quad Sphere", 'SPHERE'),
    ('CUBE', "Cube", 'MESH_CUBE'),
    ('CYLINDER', "Cylinder", 'MESH_CYLINDER'),
    ('CONE', "Cone", 'MESH_CONE'),
    ('TORUS', "Torus", 'MESH_TORUS'),
    ('PLANE', "Plane", 'MESH_PLANE'),
)


def build_torus(bm, major, minor, ratio):
    big, small = 1.0 / (1.0 + ratio), ratio / (1.0 + ratio)
    rows = []
    for i in range(major):
        a = 2 * math.pi * i / major
        ring = []
        for j in range(minor):
            b = 2 * math.pi * j / minor
            r = big + small * math.cos(b)
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), small * math.sin(b))))
        rows.append(ring)
    for i in range(major):
        for j in range(minor):
            a, b = rows[i][j], rows[(i + 1) % major][j]
            c, d = rows[(i + 1) % major][(j + 1) % minor], rows[i][(j + 1) % minor]
            bm.faces.new((a, b, c, d))


class _PrimitiveProps:
    primitive: EnumProperty(name="Примитив", items=[(p[0], p[1], "", p[2], i) for i, p in enumerate(PRIMITIVES)])
    fit: EnumProperty(name="Размер", default='PIECE', items=(
        ('PIECE', "По куску", "Ровные пропорции, размером с самый крупный заменяемый кусок"),
        ('BOUNDS', "По габаритам", "Растянуть по габаритам заменяемого"),
        ('NONE', "Стандартный", "Радиус 1")))
    segments: IntProperty(name="Сегменты", default=32, min=3, max=512)
    rings: IntProperty(name="Кольца", default=16, min=3, max=256)
    subdivisions: IntProperty(name="Подразделения", default=8, min=0, max=128)
    top_ratio: FloatProperty(name="Верх / низ", default=0.0, min=0.0, max=1.0)
    minor_segments: IntProperty(name="Сегменты трубки", default=16, min=3, max=256)
    minor_ratio: FloatProperty(name="Толщина", default=0.33, min=0.01, max=1.0)
    use_center: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})
    center: FloatVectorProperty(size=3, options={'HIDDEN', 'SKIP_SAVE'})

    def params(self):
        return {k: (tuple(getattr(self, k)) if k == "center" else getattr(self, k)) for k in (
            "primitive", "fit", "segments", "rings", "subdivisions", "top_ratio", "minor_segments", "minor_ratio",
            "use_center", "center")}

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "primitive")
        col.prop(self, "fit")
        p = self.primitive
        if p == 'UV_SPHERE':
            col.prop(self, "segments"); col.prop(self, "rings")
        elif p in ('QUAD_SPHERE', 'CUBE', 'PLANE'):
            col.prop(self, "subdivisions")
        elif p in ('CYLINDER', 'CONE'):
            col.prop(self, "segments")
            if p == 'CONE':
                col.prop(self, "top_ratio")
        elif p == 'TORUS':
            col.prop(self, "segments"); col.prop(self, "minor_segments"); col.prop(self, "minor_ratio")

    def build(self, bm):
        p = self.primitive
        if p == 'UV_SPHERE':
            bmesh.ops.create_uvsphere(bm, u_segments=self.segments, v_segments=self.rings, radius=1.0)
        elif p in ('QUAD_SPHERE', 'CUBE'):
            bmesh.ops.create_cube(bm, size=2.0)
            cuts = self.subdivisions if p == 'CUBE' else max(1, self.subdivisions)
            if cuts:
                bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
            if p == 'QUAD_SPHERE':
                for v in bm.verts:
                    v.co.normalize()
        elif p in ('CYLINDER', 'CONE'):
            top = 1.0 if p == 'CYLINDER' else self.top_ratio
            bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=self.segments,
                                  radius1=1.0, radius2=top, depth=2.0)
        elif p == 'TORUS':
            build_torus(bm, self.segments, self.minor_segments, self.minor_ratio)
        elif p == 'PLANE':
            bmesh.ops.create_grid(bm, x_segments=self.subdivisions + 1, y_segments=self.subdivisions + 1, size=1.0)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)

    def primitive_mesh(self, center, size, bounds=None):
        """Временный меш примитива: центр center, наибольший габарит size (ровные пропорции) либо растянутый по bounds
        (полуразмеры). Грани плоские (без сглаживания)."""
        bm = bmesh.new()
        self.build(bm)
        plo = Vector((min(v.co[i] for v in bm.verts) for i in range(3)))
        phi = Vector((max(v.co[i] for v in bm.verts) for i in range(3)))
        pc, ph = (plo + phi) / 2, (phi - plo) / 2
        norm = max(ph) or 1.0
        if bounds is not None:
            big = max(bounds) or 1.0
            target = Vector((bounds[i] if bounds[i] > 1e-6 else big for i in range(3)))
            scale = Vector((target[i] / ph[i] if ph[i] > 1e-6 else 1.0 / norm for i in range(3)))
            if self.primitive in ('TORUS', 'PLANE'):
                scale.z = (scale.x + scale.y) / 2      # толщину тора и плоскости не раздувать по высоте
        else:
            scale = Vector((size / 2 / norm,) * 3)
        for v in bm.verts:
            v.co = Vector(((v.co[i] - pc[i]) * scale[i] for i in range(3))) + center
        for f in bm.faces:
            f.smooth = False
        me = bpy.data.meshes.new("sculpt_fund_tmp")
        bm.to_mesh(me)
        bm.free()
        return me


def face_vertex_arrays(me):
    import numpy as np
    nf = len(me.polygons)
    starts = np.empty(nf, dtype=np.int64)
    me.polygons.foreach_get("loop_start", starts)
    totals = np.empty(nf, dtype=np.int64)
    me.polygons.foreach_get("loop_total", totals)
    cv = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", cv)
    return starts, totals, cv


def face_pieces(me, sel):
    """Связные куски выбранных граней (по общим вершинам): метка-корень на каждую вершину выбранных граней.
    Union-find на numpy. Возвращает (корень каждой вершины, вершины выбранных граней)."""
    import numpy as np
    nv, nf = len(me.vertices), len(me.polygons)
    starts, totals, cv = face_vertex_arrays(me)
    face_of = np.repeat(np.arange(nf), totals)
    sel_c = sel[face_of]
    a = cv[sel_c]
    b = cv[starts][face_of][sel_c]
    parent = np.arange(nv)
    while True:
        pa, pb = parent[a], parent[b]
        if not (pa != pb).any():
            break
        lo = np.minimum(pa, pb)
        np.minimum.at(parent, pa, lo)
        np.minimum.at(parent, pb, lo)
        while True:
            pp = parent[parent]
            if (pp == parent).all():
                break
            parent = pp
    return parent, np.unique(a)


def largest_piece(me, sel):
    """Наибольший габарит самого крупного куска среди выбранных граней и габариты всех выбранных (lo, hi)."""
    import numpy as np
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    parent, verts = face_pieces(me, sel)
    roots = parent[verts]
    order = np.argsort(roots, kind='stable')
    roots, vs = roots[order], verts[order]
    cuts = np.nonzero(np.diff(roots))[0] + 1
    best = 0.0
    for group in np.split(vs, cuts):
        p = co[group]
        best = max(best, float((p.max(axis=0) - p.min(axis=0)).max()))
    sel_co = co[verts]
    return best, Vector(sel_co.min(axis=0).tolist()), Vector(sel_co.max(axis=0).tolist())


def fresh_face_set_id(me):
    """Positive ID unused by any existing signed Face Set; operation-time only."""
    import numpy as np
    values = read_attr(me, ".sculpt_face_set", len(me.polygons), np.int32, 1).astype(np.int64)
    used = np.abs(values)
    candidate = int(used.max(initial=0)) + 1
    if candidate <= 2147483647:
        return candidate
    # INT_MIN and INT_MAX are valid inputs; avoid overflow into negative IDs.
    candidate = 1
    for value in np.unique(used):
        if value == candidate:
            candidate += 1
        elif value > candidate:
            break
    if candidate > 2147483647:
        raise RuntimeError("Нет свободного положительного Face Set ID")
    return candidate


def colored_face_set_id():
    """Номер полигруппы для нового примитива: не 1 (полигруппу 1 Blender рисует без цвета — белой) и случайный, чтобы
    у примитивов разные цвета и после Merge Down они не слились в одну группу."""
    import random
    return random.randint(2, 1 << 24)


def ensure_face_sets(me, value=1):
    import numpy as np
    layer = me.attributes.get(".sculpt_face_set")
    if layer is None:
        layer = me.attributes.new(".sculpt_face_set", 'INT', 'FACE')
        layer.data.foreach_set("value", np.full(len(me.polygons), value, dtype=np.int32))
    return layer


def separate_face_sets(meshes):
    """Перед Merge Down: номера полигрупп мешей не пересекаются (иначе части сливаются в одну группу), и нет группы 1
    (её Blender рисует белой). Меш без полигрупп получает свою. Возвращает [(меш, прежние номера или None)] для отката."""
    import numpy as np
    plans = []
    for me in meshes:
        n = len(me.polygons)
        attr = me.attributes.get(".sculpt_face_set")
        has = attr is not None and attr.domain == 'FACE' and attr.data_type == 'INT' and len(attr.data) == n
        plans.append((me, read_attr(me, ".sculpt_face_set", n, np.int32, 1) if has else np.ones(n, np.int32), has))
    next_id = max([int(np.abs(v).max(initial=1)) for _me, v, _h in plans] + [1]) + 1
    used, undo = set(), []
    for me, values, has in plans:
        mapping = {}
        for face_set in np.unique(values).tolist():
            if face_set == 1 or face_set in used:
                mapping[face_set] = next_id
                next_id += 1
            used.add(mapping.get(face_set, face_set))
        if not mapping and has:
            continue
        new = values.copy()
        for old, fresh in mapping.items():
            new[values == old] = fresh
        undo.append((me, values if has else None))
        layer = me.attributes.get(".sculpt_face_set") if has else me.attributes.new(".sculpt_face_set", 'INT', 'FACE')
        layer.data.foreach_set("value", new)
        me.update()
    return undo


def restore_face_sets(undo):
    for me, values in undo:
        attr = me.attributes.get(".sculpt_face_set")
        if values is None:
            if attr is not None:
                me.attributes.remove(attr)
        elif attr is not None:
            attr.data.foreach_set("value", values)
        me.update()


def replace_blockers(obj):
    if obj is None or obj.type != 'MESH':
        return "Нужен активный меш"
    if multires(obj) is not None:
        return "У объекта Multires: сначала примени или удали его"
    if obj.data.shape_keys:
        return "У меша есть Shape Keys: сначала удали их"
    return None


class SCULPTFUND_OT_replace_mesh(_PrimitiveProps, bpy.types.Operator):
    """Внутренний шаг: заменить примитивом незамаскированное (без маски — весь меш). Только в Object Mode"""
    bl_idname = "sculpt_fund.replace_mesh"
    bl_label = "Replace Mesh with Primitive"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'OBJECT'

    def execute(self, context):
        import numpy as np
        obj = context.active_object
        err = replace_blockers(obj)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        me = obj.data
        nf = len(me.polygons)
        sel = unmasked_faces(me) if nf else np.zeros(0, dtype=bool)
        if nf and not sel.any():
            self.report({'INFO'}, "Всё замаскировано: заменять нечего")
            return {'CANCELLED'}
        whole = nf == 0 or bool(sel.all())
        if nf:
            size, lo, hi = largest_piece(me, sel)
        else:
            size, lo, hi = 2.0, Vector((-1, -1, -1)), Vector((1, 1, 1))
        center = Vector(self.center) if self.use_center else (lo + hi) / 2
        if self.fit == 'NONE':
            size = 2.0
        tmp = self.primitive_mesh(center, size or 2.0, bounds=(hi - lo) / 2 if self.fit == 'BOUNDS' else None)
        new_set = fresh_face_set_id(me)
        bm = bmesh.new()
        if not whole:
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(sel)[0]], context='FACES')
        # BMesh appends may prepend new elements in the exported Mesh; never
        # distinguish old/new geometry by index ranges. Keep element identities.
        # Allocate layers BEFORE holding BMesh element wrappers: adding a layer
        # invalidates existing Python BMFace/BMVert wrappers.
        old_sets = bm.faces.layers.int.get(".sculpt_face_set")
        if old_sets is None:
            old_sets = bm.faces.layers.int.new(".sculpt_face_set")
            for face in bm.faces:
                face[old_sets] = 1
        had_mask = me.attributes.get(".sculpt_mask") is not None
        old_mask = bm.verts.layers.float.get(".sculpt_mask")
        if had_mask and old_mask is None:
            old_mask = bm.verts.layers.float.new(".sculpt_mask")
        keep_sets = {face: face[old_sets] for face in bm.faces}
        keep_mask = {vert: vert[old_mask] if old_mask is not None else 0.0 for vert in bm.verts}
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        face_sets = bm.faces.layers.int[".sculpt_face_set"]
        for face in bm.faces:
            face[face_sets] = keep_sets.get(face, new_set)
        if had_mask:
            mask_layer = bm.verts.layers.float[".sculpt_mask"]
            for vert in bm.verts:
                vert[mask_layer] = keep_mask.get(vert, 0.0)
        if whole:
            me.clear_geometry()
        bm.to_mesh(me)
        bm.free()
        me.update()
        return {'FINISHED'}


_step_notes = []        # (иконка, текст) от внутренних шагов таймера — показать пользователю после шага


def notify(window, text, icon='INFO'):
    """Сообщение из таймера: отчёты операторов, вызванных из Python, Blender в строку состояния не выводит (только
    в консоль) — поэтому всплывающее окошко у пера."""
    print("Sculpt Fund:", text)

    def draw(menu, _context):
        for line in text.splitlines():
            menu.layout.label(text=line)
    try:
        with bpy.context.temp_override(window=window):
            bpy.context.window_manager.popup_menu(draw, title="Sculpt Fund", icon=icon)
    except (RuntimeError, ReferenceError, TypeError, AttributeError) as e:
        print("Sculpt Fund: popup:", e)


def _run_steps(window, area, region, obj_name, step, back_mode='SCULPT', label="step"):
    """Таймер: Object Mode → шаг (внутренний UNDO-оператор) → обратно в Sculpt. Три самостоятельных шага истории,
    как руками: смена режима внутри одного оператора ломала историю Sculpt Mode (Ctrl+Z ронял Blender).
    В режиме гизмо центр гизмо сразу в центр незамаскированного (новый примитив, оставшееся и т. п.), как иконкой."""
    _step_notes.clear()
    try:
        obj = bpy.data.objects.get(obj_name)
        if obj is None or bpy.context.view_layer.objects.active != obj:
            return None
        if area is not None and area.type == 'VIEW_3D' and (region is None or region.type != 'WINDOW'):
            region = next((r for r in area.regions if r.type == 'WINDOW'), region)      # вызов из панели N
        with bpy.context.temp_override(window=window, area=area, region=region):
            scene = bpy.context.scene
            try:
                if obj.mode != 'OBJECT':
                    mark_inner_steps(scene, True)
                    bpy.ops.object.mode_set('EXEC_DEFAULT', True, mode='OBJECT')
                try:
                    step()
                except RuntimeError as e:
                    # ERROR-отчёт внутреннего шага приходит исключением «Error: текст»
                    text = str(e).strip().splitlines()[0] if str(e).strip() else label
                    _step_notes.append(('ERROR', text.split(": ", 1)[-1] if text.startswith("Error") else text))
                mark_inner_steps(scene, False)
                if back_mode != 'OBJECT' and bpy.context.view_layer.objects.active is not None:
                    bpy.ops.object.mode_set('EXEC_DEFAULT', True, mode=back_mode)
            finally:
                mark_inner_steps(scene, False)
            _pivot["co"] = None     # новый сеанс Sculpt Mode: центр гизмо в начале координат объекта
            if back_mode == 'SCULPT' and bpy.context.mode == 'SCULPT' and gizmo_tool_active(bpy.context):
                set_pivot_unmasked(bpy.context)
    except (RuntimeError, ReferenceError, TypeError) as e:
        print("Sculpt Fund: %s:" % label, e)
    notes = list(_step_notes)
    _step_notes.clear()
    for icon, text in notes:
        notify(window, text, icon)
    return None


def _run_replace(window, area, region, obj_name, mode, params):
    _run_steps(window, area, region, obj_name,
               lambda: bpy.ops.sculpt_fund.replace_mesh('EXEC_DEFAULT', True, **params), mode, "replace")
    return None


def gizmo_center_local(context, obj):
    """Центр гизмо в координатах объекта, если сейчас режим гизмо (иначе None)."""
    if context.mode == 'SCULPT' and gizmo_tool_active(context) and _pivot["key"] == pivot_key(obj) \
            and _pivot["co"] is not None:
        return pivot_local(obj).copy()
    return None


class SCULPTFUND_OT_replace_primitive(_PrimitiveProps, bpy.types.Operator):
    """Заменить примитивом незамаскированное (Customize в ZBrush): замаскированное остаётся; ровные пропорции, размером
    с самый крупный кусок, в центре гизмо. Без маски — весь меш. Параметры — в окне перед заменой"""
    bl_idname = "sculpt_fund.replace_primitive"
    bl_label = "Replace with Primitive"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def invoke(self, context, event):
        err = replace_blockers(context.active_object)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self, width=260)

    def execute(self, context):
        obj = context.active_object
        err = replace_blockers(obj)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        c = gizmo_center_local(context, obj)
        self.use_center = c is not None
        if c is not None:
            self.center = c
        bpy.app.timers.register(functools.partial(_run_replace, context.window, context.area, context.region,
                                                  obj.name, obj.mode, self.params()), first_interval=0.0)
        return {'FINISHED'}


# --- сабтулы: добавить примитив отдельным объектом, отделить замаскированное ---------------------------------

class SCULPTFUND_OT_add_mesh_object(_PrimitiveProps, bpy.types.Operator):
    """Внутренний шаг (Object Mode): новый объект-примитив, активный и выделенный"""
    bl_idname = "sculpt_fund.add_mesh_object"
    bl_label = "Add Primitive Object"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    size: FloatProperty(default=2.0, min=1e-6)
    location: FloatVectorProperty(size=3)
    collection: StringProperty()

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        me = self.primitive_mesh(Vector(), self.size)
        ensure_face_sets(me, colored_face_set_id())     # не 1: группу 1 Blender рисует белой
        name = next(p[1] for p in PRIMITIVES if p[0] == self.primitive)
        me.name = name
        obj = bpy.data.objects.new(name, me)
        obj.location = self.location
        coll = bpy.data.collections.get(self.collection) or context.collection or context.scene.collection
        coll.objects.link(obj)
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        return {'FINISHED'}


class SCULPTFUND_OT_add_primitive(_PrimitiveProps, bpy.types.Operator):
    """Добавить примитив отдельным объектом (Append сабтула в ZBrush): в центр гизмо (без гизмо — в центр текущего
    объекта), размером в четверть текущего объекта; он сразу активен в Sculpt Mode, назад — Alt+клик"""
    bl_idname = "sculpt_fund.add_primitive"
    bl_label = "Add Primitive Object"

    @classmethod
    def poll(cls, context):
        return context.mode in ('SCULPT', 'OBJECT')

    def execute(self, context):
        obj = context.active_object
        loc, size, coll = Vector(), 2.0, ""
        if obj is not None and obj.type == 'MESH':
            pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            lo = Vector((min(q[i] for q in pts) for i in range(3)))
            hi = Vector((max(q[i] for q in pts) for i in range(3)))
            size = max(max(hi - lo) / 4, 1e-3)
            c = gizmo_center_local(context, obj)
            loc = obj.matrix_world @ c if c is not None else (lo + hi) / 2
            coll = obj.users_collection[0].name if obj.users_collection else ""
        params = dict(self.params(), size=size, location=tuple(loc), collection=coll)
        params.pop("use_center"); params.pop("center")
        mode = context.mode if context.mode == 'SCULPT' else 'OBJECT'
        name = obj.name if obj is not None else ""

        def step():
            bpy.ops.sculpt_fund.add_mesh_object('EXEC_DEFAULT', True, **params)
        if obj is None or mode == 'OBJECT':
            safe(bpy.ops.sculpt_fund.add_mesh_object, 'EXEC_DEFAULT', True, report=self.report, **params)
            return {'FINISHED'}
        bpy.app.timers.register(functools.partial(_run_steps, context.window, context.area, context.region, name,
                                                  step, 'SCULPT', "add"), first_interval=0.0)
        return {'FINISHED'}


def _closed_component_volumes(bm):
    """Yield (faces, signed volume, scale) for each edge-connected component."""
    remaining_faces = set(bm.faces)
    while remaining_faces:
        seed = remaining_faces.pop()
        component = [seed]
        stack = [seed]
        while stack:
            face = stack.pop()
            for edge in face.edges:
                for other in edge.link_faces:
                    if other in remaining_faces:
                        remaining_faces.remove(other)
                        stack.append(other)
                        component.append(other)
        reference = component[0].verts[0].co
        volume = 0.0
        for face in component:
            p0 = face.verts[0].co - reference
            for i in range(1, len(face.verts) - 1):
                p1 = face.verts[i].co - reference
                p2 = face.verts[i + 1].co - reference
                volume += p0.dot(p1.cross(p2)) / 6.0
        vertices = {v for face in component for v in face.verts}
        size = max(max(v.co[a] for v in vertices) - min(v.co[a] for v in vertices) for a in range(3))
        yield component, volume, size


def remesh_closed_volume(mesh):
    """Validate a nonempty closed mesh; return sum of absolute component volumes.

    This is a topology/volume safety check, not a geometric self-intersection
    solver. Never changes input. Use on prepared input and native-remesh output.
    """
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        if not bm.verts or not bm.faces:
            raise ValueError("Ремеш не создал поверхность; уменьшите Voxel Size")
        if any(not math.isfinite(c) for v in bm.verts for c in v.co):
            raise ValueError("Результат содержит некорректные координаты")
        if any(not e.is_manifold for e in bm.edges) or any(not v.is_manifold for v in bm.verts):
            raise ValueError("Результат ремеша не замкнут; исходная сетка сохранена")
        total = 0.0
        for faces, volume, size in _closed_component_volumes(bm):
            if not math.isfinite(volume) or abs(volume) <= max(size ** 3 * 1e-12, 1e-30):
                raise ValueError("Результат ремеша не ограничивает объём")
            total += abs(volume)
        return total
    finally:
        bm.free()


def validate_remesh_result(mesh, reference_volume):
    """Reject an empty/nonmanifold result or catastrophic (>99%) volume loss.

    A coarse voxel size may legitimately merge islands or erase tiny details;
    those are not inferred from topology/component count. Gross collapse of the
    entire solid is treated as failure and caller keeps the original mesh.
    """
    volume = remesh_closed_volume(mesh)
    if reference_volume is None:        # исходник с изъяном: объёма для сравнения нет, проверяется только результат
        return volume
    if not math.isfinite(reference_volume) or reference_volume <= 0:
        raise ValueError("Некорректный исходный объём для ремеша")
    if volume < reference_volume * .01:
        raise ValueError("Ремеш потерял почти весь объём; уменьшите Voxel Size")
    return volume


def prepare_closed_remesh_mesh(mesh):
    """Return (independent repaired mesh or None, number of capped loops).

    Supports manifold surfaces with simple, disjoint boundary loops. Does not
    infer a desired solid for branching, wire, zero-volume or degenerate input.
    Never changes mesh; failures raise ValueError with a useful reason.
    """
    bm = bmesh.new()
    prepared = None
    try:
        bm.from_mesh(mesh)
        if not bm.verts or not bm.faces:
            raise ValueError("Нет поверхности для ремеша")
        if any(not math.isfinite(c) for v in bm.verts for c in v.co):
            raise ValueError("В сетке есть некорректные координаты")
        extent = max(max(v.co[a] for v in bm.verts) - min(v.co[a] for v in bm.verts) for a in range(3))
        if extent <= 0:
            raise ValueError("Нулевой размер сетки")
        edge_epsilon = max(extent * 1e-9, 1e-12)
        area_epsilon = edge_epsilon * edge_epsilon
        if any(e.calc_length() <= edge_epsilon for e in bm.edges) or any(f.calc_area() <= area_epsilon for f in bm.faces):
            raise ValueError("Есть вырожденные рёбра или грани; очистите сетку перед ремешем")
        if any(len(e.link_faces) not in (1, 2) for e in bm.edges) or any(not v.link_faces for v in bm.verts):
            raise ValueError("Есть свободные элементы или рёбра с несколькими поверхностями")
        boundary = [e for e in bm.edges if e.is_boundary]
        if not boundary:
            if any(not v.is_manifold for v in bm.verts):
                raise ValueError("Есть немногообразные вершины; автоматическое закрытие невозможно")
            return None, 0

        # Every boundary vertex must belong to exactly one simple closed cycle.
        by_vertex = {}
        for edge in boundary:
            for vert in edge.verts:
                by_vertex.setdefault(vert, []).append(edge)
        if any(len(edges) != 2 for edges in by_vertex.values()):
            raise ValueError("Граница ветвится; автоматическое закрытие невозможно")
        remaining = set(boundary)
        loops = []
        while remaining:
            seed = next(iter(remaining))
            loop = []
            stack = [seed]
            remaining.remove(seed)
            while stack:
                edge = stack.pop()
                loop.append(edge)
                for vert in edge.verts:
                    for other in by_vertex[vert]:
                        if other in remaining:
                            remaining.remove(other)
                            stack.append(other)
            if len(loop) < 3:
                raise ValueError("Граница содержит меньше трёх рёбер")
            loops.append(loop)

        caps = []
        for loop in loops:
            faces = bmesh.ops.holes_fill(bm, edges=loop, sides=0).get('faces', [])
            if not faces:
                raise ValueError("Не удалось закрыть отверстие")
            caps.extend(faces)
        # Explicit triangles avoid relying on n-gon tessellation during voxelization.
        bmesh.ops.triangulate(bm, faces=caps)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if any(not e.is_manifold for e in bm.edges) or any(not v.is_manifold for v in bm.verts):
            raise ValueError("После закрытия сетка остаётся немногобразной")
        if any(f.calc_area() <= area_epsilon for f in bm.faces):
            raise ValueError("Закрытие отверстия создаёт вырожденные грани")

        # Validate each connected solid separately: a sheet can be capped into
        # coincident opposite faces yet still have no usable enclosed volume.
        for component, volume, size in _closed_component_volumes(bm):
            if abs(volume) <= max(size ** 3 * 1e-12, 1e-30):
                raise ValueError("Поверхность не ограничивает объём; задайте толщину вручную")
            if volume < 0:
                bmesh.ops.reverse_faces(bm, faces=component)

        prepared = mesh.copy()
        bm.to_mesh(prepared)
        prepared.update()
        return prepared, len(loops)
    except Exception:
        if prepared is not None:
            bpy.data.meshes.remove(prepared)
        raise
    finally:
        bm.free()


def strip_loose(mesh):
    """Копия меша без рёбер и вершин, у которых нет граней (ремешу они не нужны, а закрыть отверстия мешают);
    None — таких нет."""
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        wires = [e for e in bm.edges if not e.link_faces]
        if wires:
            bmesh.ops.delete(bm, geom=wires, context='EDGES')
        loose = [v for v in bm.verts if not v.link_faces]
        if not wires and not loose:
            return None
        if loose:
            bmesh.ops.delete(bm, geom=loose, context='VERTS')
        out = mesh.copy()
        bm.to_mesh(out)
        out.update()
        return out
    finally:
        bm.free()


def approx_volume(mesh):
    """Объём и незамкнутой сетки (по теореме о дивергенции) — мерка для ремеша «как есть»."""
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        return abs(bm.calc_volume(signed=True))
    finally:
        bm.free()


class SCULPTFUND_OT_voxel_remesh_mesh(bpy.types.Operator):
    """Object Mode data step. Work on a disposable object until validation passes."""
    bl_idname = "sculpt_fund.voxel_remesh_mesh"
    bl_label = "Закрыть отверстия и выполнить Voxel Remesh"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'OBJECT'

    def execute(self, context):
        obj = context.active_object
        err = replace_blockers(obj)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        source = obj.data
        selected = list(context.selected_objects)
        scratch = None
        candidate = None
        cleaned = None
        open_reason = None
        try:
            try:
                candidate, caps = prepare_closed_remesh_mesh(source)
            except ValueError as exc:
                # Сетка с изъяном (ребро на три грани после Symmetrize, «провод», вырожденные грани и т. п.). Раньше
                # ремеш отменялся, а причина уходила только в консоль («не пересчитывается», 21.10.2026). Теперь:
                # провода и вершины без граней долой и снова закрыть отверстия; не вышло — Voxel Remesh как есть
                # (он сам строит замкнутую сетку, как DynaMesh в ZBrush), с проверкой объёма ниже.
                candidate, caps, open_reason = None, 0, str(exc).rstrip(".")
                cleaned = strip_loose(source)
                if cleaned is not None:
                    try:
                        candidate, caps = prepare_closed_remesh_mesh(cleaned)
                        open_reason = None
                    except ValueError as exc2:
                        open_reason = str(exc2).rstrip(".")
                    if candidate is None:
                        candidate, cleaned = cleaned, None
            candidate = candidate if candidate is not None else source.copy()
            before = approx_volume(candidate) if open_reason else remesh_closed_volume(candidate)
            scratch = bpy.data.objects.new("Sculpt Fund remesh check", candidate)
            context.collection.objects.link(scratch)
            # Work in local mesh units exactly like the native operator.
            for item in selected:
                item.select_set(False)
            scratch.select_set(True)
            context.view_layer.objects.active = scratch
            result = bpy.ops.object.voxel_remesh('EXEC_DEFAULT')
            if 'FINISHED' not in result:
                raise ValueError("Blender не выполнил Voxel Remesh")
            after = validate_remesh_result(scratch.data, None if open_reason else before)
            if open_reason and before > 0 and after < before * 0.5:
                # отверстие, которое не закрылось: Voxel Remesh делает из него тонкую оболочку
                raise ValueError("Ремеш как есть потерял бы больше половины объёма (%s)" % open_reason)
            # Commit only after topology and gross-volume checks.
            obj.data = scratch.data
            _pivot["co"] = None
            self.report({'INFO'}, "Voxel Remesh выполнен" + ("; закрыто отверстий: %d" % caps if caps else ""))
            if open_reason:
                _step_notes.append(('INFO', "Voxel Remesh выполнен как есть, без закрытия отверстий: " + open_reason))
            return {'FINISHED'}
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc) + ". Исходная сетка сохранена")
            return {'CANCELLED'}
        finally:
            if scratch is not None:
                bpy.data.objects.remove(scratch, do_unlink=True)
            if candidate is not None and candidate.users == 0:
                bpy.data.meshes.remove(candidate)
            if cleaned is not None and cleaned.users == 0:
                bpy.data.meshes.remove(cleaned)
            for item in selected:
                item.select_set(True)
            context.view_layer.objects.active = obj


class SCULPTFUND_OT_dyna_popup(bpy.types.Operator):
    """Ctrl+R: окно DynaMesh — Resolution и Voxel Size, с которыми пройдёт ремеш. Сам ремеш — Ctrl+протяжка
    по пустому месту (как в ZBrush) или кнопка Remesh здесь"""
    bl_idname = "sculpt_fund.dyna_popup"
    bl_label = "DynaMesh"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode in {'OBJECT', 'SCULPT'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=300)

    def draw(self, context):
        obj = context.active_object
        col = self.layout.column()
        col.label(text="DynaMesh: " + obj.name, icon='MOD_REMESH')
        col.prop(obj, "sculpt_fund_dyna_res", text="Resolution", slider=True)
        col.prop(obj.data, "remesh_voxel_size", text="Voxel Size")
        col.label(text="Ремеш — Ctrl+протяжка по пустому месту")
        col.operator(SCULPTFUND_OT_voxel_remesh.bl_idname, text="Remesh сейчас", icon='MOD_REMESH')

    def execute(self, context):
        return {'FINISHED'}


class SCULPTFUND_OT_voxel_remesh(bpy.types.Operator):
    """Автоматически закрыть простые отверстия, проверить результат и выполнить Voxel Remesh"""
    bl_idname = "sculpt_fund.voxel_remesh"
    bl_label = "Voxel Remesh — закрыть отверстия"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode in {'OBJECT', 'SCULPT'}

    def execute(self, context):
        obj = context.active_object
        err = replace_blockers(obj)
        if getattr(obj, "use_dynamic_topology_sculpting", False):
            err = "Сначала выключите Dyntopo"
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        if context.mode == 'OBJECT':
            _step_notes.clear()
            res = safe(bpy.ops.sculpt_fund.voxel_remesh_mesh, 'EXEC_DEFAULT', True, report=self.report)
            for _icon, text in _step_notes:
                self.report({'INFO'}, text)
            _step_notes.clear()
            return res
        area = context.area
        if area is None or area.type != 'VIEW_3D':
            area = next((a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
        if area is None:
            self.report({'ERROR'}, "Откройте 3D Viewport")
            return {'CANCELLED'}
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        bpy.app.timers.register(functools.partial(
            _run_steps, context.window, area, region, obj.name,
            lambda: bpy.ops.sculpt_fund.voxel_remesh_mesh('EXEC_DEFAULT', True),
            'SCULPT', "safe remesh"), first_interval=0.0)
        return {'FINISHED'}


def masked_face_flags(me):
    """Замаскированные грани: средняя маска вершин грани ≥ 0,5."""
    import numpy as np
    nv, nf = len(me.vertices), len(me.polygons)
    mask = read_attr(me, ".sculpt_mask", nv, np.float32, 0.0)
    starts, totals, cv = face_vertex_arrays(me)
    return np.add.reduceat(mask[cv], starts) / np.maximum(totals, 1) >= 0.5


class SCULPTFUND_OT_split_masked_mesh(bpy.types.Operator):
    """Внутренний шаг (Object Mode): замаскированное — в новый объект, в исходном остаётся незамаскированное"""
    bl_idname = "sculpt_fund.split_masked_mesh"
    bl_label = "Split Masked"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'OBJECT'

    def execute(self, context):
        import numpy as np
        obj = context.active_object
        err = replace_blockers(obj)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        masked = masked_face_flags(obj.data)
        if not masked.any() or masked.all():
            self.report({'INFO'}, "Нужна маска на части меша")
            return {'CANCELLED'}
        pieces = []
        open_reason = None
        try:
            for drop in (masked, ~masked):
                me = obj.data.copy()
                pieces.append(me)
                bm = bmesh.new()
                try:
                    bm.from_mesh(me)
                    bm.faces.ensure_lookup_table()
                    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(drop)[0]], context='FACES')
                    bm.to_mesh(me)
                finally:
                    bm.free()
                # Закрыть границу — по возможности. Сетка с изъянами (ребро на три грани после Symmetrize, вершина-
                # «бабочка» и т. п.) не закрывается, но отделять это не мешает: кусок остаётся с открытой границей,
                # как в ZBrush (раньше вся операция отменялась, а сообщение уходило только в консоль)
                try:
                    closed, _caps = prepare_closed_remesh_mesh(me)
                except ValueError as exc:
                    closed = None
                    open_reason = open_reason or str(exc)
                if closed is not None:
                    pieces[-1] = closed
                    bpy.data.meshes.remove(me)
                    me = closed
                a = me.attributes.get(".sculpt_mask")
                if a is not None:
                    a.data.foreach_set("value", np.zeros(len(me.vertices), dtype=np.float32))
                me.update()
        except (ValueError, RuntimeError) as exc:
            for me in pieces:
                if me.users == 0:
                    bpy.data.meshes.remove(me)
            self.report({'ERROR'}, str(exc) + ". Отделение отменено, исходная сетка сохранена")
            return {'CANCELLED'}
        new = obj.copy()
        new.data = pieces[1]
        new.name = obj.name + ".masked"
        for coll in obj.users_collection:
            coll.objects.link(new)
        obj.data = pieces[0]
        new.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        if open_reason:
            msg = "Отделено в «%s». Границу не закрыл: %s" % (new.name, open_reason.rstrip("."))
            self.report({'WARNING'}, msg)
            _step_notes.append(('INFO', msg))
        return {'FINISHED'}


class SCULPTFUND_OT_split_masked(bpy.types.Operator):
    """Отделить замаскированное в отдельный объект; границу обеих частей закрыть, если сетка позволяет.
    Маска снимается; активным остаётся исходный, переход — Alt+клик"""
    bl_idname = "sculpt_fund.split_masked"
    bl_label = "Отделить замаскированное"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode in ('SCULPT', 'OBJECT')

    def execute(self, context):
        obj = context.active_object
        err = replace_blockers(obj)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        if mesh_readable(obj):
            m = masked_face_flags(obj.data)
            if not m.any() or m.all():
                self.report({'INFO'}, "Нужна маска на части меша")
                return {'CANCELLED'}
        mode = 'SCULPT' if context.mode == 'SCULPT' else 'OBJECT'
        bpy.app.timers.register(functools.partial(
            _run_steps, context.window, context.area, context.region, obj.name,
            lambda: bpy.ops.sculpt_fund.split_masked_mesh('EXEC_DEFAULT', True), mode, "split"), first_interval=0.0)
        return {'FINISHED'}


def merge_down_name_key(obj):
    import re
    # Natural ordering (Part2 before Part10); exact name breaks case/zero ties.
    return (tuple((1, int(p)) if p.isdigit() else (0, p.casefold())
                  for p in re.split(r'(\d+)', obj.name)), obj.name)


def merge_down_plan(context):
    """Return (target, reason). Direct collection children only; never wrap."""
    obj = context.active_object
    if obj is None or obj.type != 'MESH' or context.mode not in {'OBJECT', 'SCULPT'}:
        return None, "Нужен активный меш в Object или Sculpt Mode"
    coll = context.collection
    if coll is None or coll.objects.get(obj.name) != obj:
        if len(obj.users_collection) != 1:
            return None, "Объект в нескольких коллекциях: выберите его коллекцию"
        coll = obj.users_collection[0]
    candidates = sorted((o for o in coll.objects
                         if o.type == 'MESH' and context.view_layer.objects.get(o.name) == o
                         and o.visible_get(view_layer=context.view_layer)
                         and not o.hide_select and o.is_editable and o.data.is_editable),
                        key=merge_down_name_key)
    if obj not in candidates:
        return None, "Активный меш скрыт, недоступен для выбора или редактирования"
    index = candidates.index(obj) + 1
    if index == len(candidates):
        return None, "Ниже нет видимого доступного меша в коллекции «%s»" % coll.name
    target = candidates[index]
    for item in (obj, target):
        if item.modifiers:
            return None, "«%s»: сначала примените или удалите модификаторы" % item.name
        if item.data.shape_keys is not None:
            return None, "«%s»: объединение с Shape Keys не поддерживается" % item.name
        if item.data.users > 1:
            return None, "«%s»: сначала сделайте меш однопользовательским" % item.name
        if getattr(item, 'use_dynamic_topology_sculpting', False):
            return None, "«%s»: сначала выключите Dyntopo" % item.name
    if abs(obj.matrix_world.determinant()) < 1e-12:
        return None, "Активный объект имеет нулевой масштаб"
    return target, ""


def merge_down_join(context, obj, target, report):
    """Object-mode step; revalidate captured target before changing selection."""
    current, reason = merge_down_plan(context)
    if context.mode != 'OBJECT' or context.active_object != obj:
        report({'WARNING'}, "Merge Down: активный объект или режим изменился")
        return {'CANCELLED'}
    if reason or current != target:
        report({'WARNING'}, reason or "Merge Down: сосед изменился; запустите команду заново")
        return {'CANCELLED'}
    selected = list(context.selected_objects)
    for other in selected:
        other.select_set(False)
    obj.select_set(True)
    target.select_set(True)
    name = target.name
    # Полигруппы частей не сливаются и ни одна не белая. Правка до join без своего шага истории: шаг Join в Object
    # Mode — снимок всего файла, Ctrl+Z возвращает и прежние номера (t54)
    face_set_undo = separate_face_sets([obj.data, target.data])
    result = safe(bpy.ops.object.join, 'EXEC_DEFAULT', True, report=report)
    if result != {'FINISHED'}:
        restore_face_sets(face_set_undo)
        for other in context.selected_objects:
            other.select_set(False)
        for other in selected:
            other.select_set(True)
        context.view_layer.objects.active = obj
        return {'CANCELLED'}
    report({'INFO'}, "Merge Down: «%s» → «%s». Без ремеша" % (name, obj.name))
    return result


def merge_down_report(levels, message):
    # Timer outlives wrapper RNA. Native join must remain a top-level operator
    # for redo to restore geometry; a reporting dispatcher would nest join.
    print("Sculpt Fund:", '/'.join(sorted(levels)), message)


def merge_down_step(source_name, target_name):
    obj = bpy.data.objects.get(source_name)
    target = bpy.data.objects.get(target_name)
    if obj is None or target is None:
        merge_down_report({'WARNING'}, "Merge Down: объект удалён или переименован; запустите команду заново")
        return {'CANCELLED'}
    return merge_down_join(bpy.context, obj, target, merge_down_report)


class SCULPTFUND_OT_merge_down(bpy.types.Operator):
    """Объединить с нижним видимым мешем по имени в текущей коллекции, без ремеша"""
    bl_idname = "sculpt_fund.merge_down"
    bl_label = "Merge Down"
    # Do not add UNDO: object.join and mode_set must stay independent steps.

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode in {'SCULPT', 'OBJECT'}

    @classmethod
    def description(cls, context, properties):
        target, reason = merge_down_plan(context)
        return reason or ("Merge Down → «%s»: объединить без ремеша; порядок по имени" % target.name)

    def execute(self, context):
        obj = context.active_object
        target, reason = merge_down_plan(context)
        if reason:
            self.report({'WARNING'}, reason)
            return {'CANCELLED'}
        window, area, region = context.window, context.area, context.region
        if window is None or area is None or area.type != 'VIEW_3D' or region is None:
            self.report({'WARNING'}, "Запустите Merge Down в 3D View")
            return {'CANCELLED'}
        mode, source_name, target_name = obj.mode, obj.name, target.name
        # Capture strings only: operator RNA expires when execute returns.
        step = functools.partial(merge_down_step, source_name, target_name)
        bpy.app.timers.register(functools.partial(
            _run_steps, window, area, region, source_name, step, mode, "merge down"), first_interval=0.0)
        self.report({'INFO'}, "Merge Down → «%s»: объединение без ремеша" % target_name)
        return {'FINISHED'}


def symmetrize_label(direction):
    """'NEGATIVE_X' → «−X → +X (слева направо)»: откуда Symmetrize копирует; лево/право — как на виде спереди."""
    axis = direction[-1]
    if direction.startswith('NEGATIVE'):
        text, side = "−%s → +%s" % (axis, axis), " (слева направо)"
    else:
        text, side = "+%s → −%s" % (axis, axis), " (справа налево)"
    return text + (side if axis == 'X' else "")


class SCULPTFUND_OT_symmetrize_side(bpy.types.Operator):
    """Symmetrize с выбранной стороны: одна половина меша копируется на другую (штатный Symmetrize, его Direction).
    Лево и право — как на виде спереди"""
    bl_idname = "sculpt_fund.symmetrize_side"
    bl_label = "Symmetrize"
    bl_options = {'REGISTER'}       # шаг истории пишет штатный Symmetrize (см. mask_click)

    side: EnumProperty(items=(('NEGATIVE', "−X → +X", "Левую половину на правую"),
                              ('POSITIVE', "+X → −X", "Правую половину на левую")))

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return context.mode == 'SCULPT' and obj is not None and obj.type == 'MESH'

    @classmethod
    def description(cls, context, properties):
        axis = context.tool_settings.sculpt.symmetrize_direction[-1]
        return "Symmetrize " + symmetrize_label(properties.side + "_" + axis) + ": копирует эту половину меша на другую"

    def execute(self, context):
        sculpt = context.tool_settings.sculpt
        sculpt.symmetrize_direction = self.side + "_" + sculpt.symmetrize_direction[-1]
        res = safe(bpy.ops.sculpt.symmetrize, 'EXEC_DEFAULT', True, report=self.report)
        if res != {'FINISHED'}:
            return {'CANCELLED'}
        self.report({'INFO'}, "Symmetrize " + symmetrize_label(sculpt.symmetrize_direction))
        return {'FINISHED'}


def delete_hidden_blockers(obj):
    err = replace_blockers(obj)
    if err:
        return err
    if obj.use_dynamic_topology_sculpting:
        return "Сначала выключите Dyntopo"
    return None


class SCULPTFUND_OT_delete_hidden_mesh(bpy.types.Operator):
    """Внутренний шаг (Object Mode): удалить скрытые грани, оставшееся видно"""
    bl_idname = "sculpt_fund.delete_hidden_mesh"
    bl_label = "Del Hidden"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'OBJECT'

    def execute(self, context):
        import numpy as np
        obj = context.active_object
        err = delete_hidden_blockers(obj)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        me = obj.data
        hidden = read_attr(me, ".hide_poly", len(me.polygons), bool, False)
        if not hidden.any():
            self.report({'INFO'}, "Скрытого нет")
            return {'CANCELLED'}
        if hidden.all():
            self.report({'ERROR'}, "Скрыт весь меш: после удаления ничего не останется")
            return {'CANCELLED'}
        bm = bmesh.new()
        try:
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            # FACES: вместе с гранями уходят рёбра и вершины, которые были только у них; маска и полигруппы
            # остального — слоями BMesh
            bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(hidden)[0]], context='FACES')
            bm.to_mesh(me)
        finally:
            bm.free()
        for name in (".hide_vert", ".hide_edge", ".hide_poly"):
            attr = me.attributes.get(name)
            if attr is not None:
                me.attributes.remove(attr)
        me.update()
        return {'FINISHED'}


class SCULPTFUND_OT_delete_hidden(bpy.types.Operator):
    """Del Hidden, как в ZBrush: удалить скрытое (Ctrl+Shift), видимое остаётся"""
    bl_idname = "sculpt_fund.delete_hidden"
    bl_label = "Del Hidden"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode in ('SCULPT', 'OBJECT')

    def execute(self, context):
        obj = context.active_object
        err = delete_hidden_blockers(obj)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        if mesh_readable(obj):
            hidden = read_attr(obj.data, ".hide_poly", len(obj.data.polygons), bool, False)
            if not hidden.any():
                self.report({'INFO'}, "Скрытого нет: спрячьте лишнее Ctrl+Shift")
                return {'CANCELLED'}
            if hidden.all():
                self.report({'ERROR'}, "Скрыт весь меш: после удаления ничего не останется")
                return {'CANCELLED'}
        mode = 'SCULPT' if context.mode == 'SCULPT' else 'OBJECT'
        bpy.app.timers.register(functools.partial(
            _run_steps, context.window, context.area, context.region, obj.name,
            lambda: bpy.ops.sculpt_fund.delete_hidden_mesh('EXEC_DEFAULT', True), mode, "del hidden"),
            first_interval=0.0)
        return {'FINISHED'}


class SCULPTFUND_MT_quick(bpy.types.Menu):
    """Tab в Sculpt Mode: Quick Favorites, Symmetrize с выбранной стороны, Del Hidden и «Отделить замаскированное»
    (убирается галочкой в панели N)"""
    bl_label = "Quick Favorites"
    bl_idname = "SCULPTFUND_MT_quick"

    def draw(self, context):
        layout = self.layout
        layout.menu_contents("SCREEN_MT_user_menu")
        # Сразу под Quick Favorites (у пользователя там Symmetrize): Symmetrize с одной и с другой стороны, сразу
        axis = context.tool_settings.sculpt.symmetrize_direction[-1]
        for side in ('NEGATIVE', 'POSITIVE'):
            layout.operator(SCULPTFUND_OT_symmetrize_side.bl_idname, icon='MOD_MIRROR',
                            text="Symmetrize " + symmetrize_label(side + "_" + axis)).side = side
        brush = context.tool_settings.sculpt.brush
        if brush is not None:
            layout.prop(brush, "use_frontface", text="BackfaceMask: " + brush.name)     # чекбокс в стиле темы
        layout.separator()
        layout.operator(SCULPTFUND_OT_delete_hidden.bl_idname, icon='TRASH')
        if prefs().split_in_quick:
            layout.operator(SCULPTFUND_OT_split_masked.bl_idname, icon='MOD_MASK')


# --- гизмо Transform (W) --------------------------------------------------------------------------------

class SCULPTFUND_OT_gizmo_tool(bpy.types.Operator):
    """W — гизмо со стрелками (Move), E — полное гизмо (стрелки, кольца, масштаб). Из кисти центр гизмо сразу ставится
    в центр незамаскированного (как Gizmo 3D в ZBrush); между W и E центр не трогается"""
    bl_idname = "sculpt_fund.gizmo_tool"
    bl_label = "Gizmo"

    tool: StringProperty(default='builtin.move')

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT'

    def execute(self, context):
        was_gizmo = gizmo_tool_active(context)
        safe(bpy.ops.wm.tool_set_by_id, name=self.tool, report=self.report)
        if not was_gizmo:
            set_pivot_unmasked(context, self.report)
        return {'FINISHED'}


def ensure_pivot(context):
    """Центр для S / G / R в режиме кисти — как у гизмо: где гизмо стоит в этом сеансе Sculpt, а если его ещё не
    ставили (новый сеанс: вход в Sculpt, шаги через Object Mode) — в центре незамаскированного, как поставит W.
    Раньше в режиме кисти поворот и масштаб шли вокруг начала координат объекта (27.10.2026)."""
    obj = context.active_object
    if obj is None or obj.type != 'MESH' or gizmo_tool_active(context):
        return
    if _pivot["key"] != pivot_key(obj) or _pivot["co"] is None:
        set_pivot_unmasked(context)


class SCULPTFUND_OT_xform_key(bpy.types.Operator):
    """G / R / S в Sculpt: перенос, поворот, масштаб незамаскированного вокруг центра гизмо (и в режиме кисти)"""
    bl_idname = "sculpt_fund.xform_key"
    bl_label = "Transform Around Gizmo Center"
    bl_options = {'INTERNAL'}

    kind: EnumProperty(items=(('TRANSLATE', "Move", ""), ('ROTATE', "Rotate", ""), ('SCALE', "Scale", "")))

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and context.region_data is not None

    def invoke(self, context, event):
        ensure_pivot(context)
        if self.kind == 'SCALE':
            op = bpy.ops.sculpt_fund.scale
        else:
            op = bpy.ops.transform.translate if self.kind == 'TRANSLATE' else bpy.ops.transform.rotate
        # модальный оператор уже работает своим обработчиком; этот — только запуск
        return {'CANCELLED'} if safe(op, 'INVOKE_DEFAULT', report=self.report) == {'CANCELLED'} else {'FINISHED'}


class SCULPTFUND_OT_pivot_unmasked(bpy.types.Operator):
    """Центр гизмо в центр незамаскированного (Unmasked Center Mesh в ZBrush)"""
    bl_idname = "sculpt_fund.pivot_unmasked"
    bl_label = "Gizmo to Unmasked Center"

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT'

    def execute(self, context):
        return set_pivot_unmasked(context, self.report)


class SCULPTFUND_OT_gizmo_world(bpy.types.Operator):
    """Оси гизмо по миру (Reset Orientation в ZBrush): ориентация Global"""
    bl_idname = "sculpt_fund.gizmo_world"
    bl_label = "Gizmo Axes to World"

    def execute(self, context):
        _pivot.pop('auto_orient', None)
        context.scene.transform_orientation_slots[0].type = 'GLOBAL'
        if context.mode == 'SCULPT':
            remember_orientation(context)
        return {'FINISHED'}


class SCULPTFUND_OT_gizmo_moved(bpy.types.Operator):
    """Центр гизмо перенесён без меша (Alt)"""
    bl_idname = "sculpt_fund.gizmo_moved"
    bl_label = "Move Gizmo Only"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        return {'FINISHED'}


class SCULPTFUND_OT_pivot_surface(bpy.types.Operator):
    """Shift+ПКМ: центр гизмо в точку на поверхности (штатный Set Pivot Position, с отслеживанием для иконок)"""
    bl_idname = "sculpt_fund.pivot_surface"
    bl_label = "Gizmo to Surface Point"

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and context.region_data is not None

    def invoke(self, context, event):
        obj = context.active_object
        p = depth_point(context, event, obj)
        res = safe(bpy.ops.sculpt.set_pivot_position, 'INVOKE_DEFAULT', mode='SURFACE', report=self.report)
        if p is not None and obj is not None and res != {'CANCELLED'}:
            pivot_store(obj, obj.matrix_world.inverted_safe() @ p)
        return res


def axis_by_color(context, color):
    """Ось ручки по цвету темы (0/1/2) или None (белая ручка — вид / центр)."""
    ui = context.preferences.themes[0].user_interface
    dist = [sum((color[i] - c[i]) ** 2 for i in range(3)) for c in (ui.axis_x, ui.axis_y, ui.axis_z)]
    best = min(dist)
    return dist.index(best) if best < 0.05 else None


def handle_kind(context, g):
    """Что за ручка под пером: ('AXIS', ось) — стрелка переноса или масштаба, ('FREE', None) — центр,
    ('ROT', ось) — кольцо оси, ('ROT_VIEW', None) — кольцо вида; (None, None) — другое."""
    if g is None:
        return None, None
    style = getattr(g, "draw_style", None)
    if g.bl_idname == 'GIZMO_GT_primitive_3d' and style == 'CIRCLE':
        return 'FREE', None
    idx = axis_by_color(context, g.color)
    if g.bl_idname == 'GIZMO_GT_arrow_3d' and style in ('NORMAL', 'BOX') and idx is not None:
        return 'AXIS', idx
    if g.bl_idname == 'GIZMO_GT_dial_3d':
        return ('ROT', idx) if idx is not None else ('ROT_VIEW', None)
    return None, None


def handle_axis(context, g):
    """Для копии: 0/1/2 — стрелка переноса (не масштаба), -1 — центр (свободно), None — другое."""
    kind, idx = handle_kind(context, g)
    if kind == 'FREE':
        return -1
    if kind == 'AXIS' and getattr(g, "draw_style", None) == 'NORMAL':
        return idx
    return None


def dup_blockers(obj):
    if obj is None or obj.type != 'MESH':
        return "Нужен активный меш"
    if multires(obj) is not None:
        return "У объекта Multires: копия гизмо работает без него"
    if obj.data.shape_keys:
        return "У меша есть Shape Keys: копия гизмо работает без них"
    return None


def xform_gizmo_hit(context):
    """Группа гизмо Transform под пером и подсвеченная ручка (в раскладке ручек гизмо), иначе (None, None)."""
    gg = getattr(context, "gizmo_group", None)
    if gg is None or gg.bl_idname != 'VIEW3D_GGT_xform_gizmo' or not len(gg.gizmos) or context.active_object is None:
        return None, None
    return gg, next((g for g in gg.gizmos if g.is_highlight), None)


DUP_DRAG_PX = 20        # Ctrl-копия начинается только после такой протяжки: короткий Ctrl+тык пером — это Ctrl+клик


class SCULPTFUND_OT_gizmo_press(bpy.types.Operator):
    """Нажатие на ручку гизмо: точный центр гизмо; Ctrl+протяжка стрелки или центра (от 20 px) — копия
    незамаскированного (вырез из меша — выдавливание), как в ZBrush"""
    bl_idname = "sculpt_fund.gizmo_press"
    bl_label = "Gizmo Handle"
    bl_options = {'INTERNAL'}

    dup: BoolProperty(default=False, options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT'

    def invoke(self, context, event):
        gg, g = xform_gizmo_hit(context)
        if gg is None:
            return {'PASS_THROUGH'}
        obj = context.active_object
        pivot_store(obj, obj.matrix_world.inverted_safe() @ Vector(gg.gizmos[0].matrix_basis.translation))
        remember_orientation(context, obj)      # оси до действия ручкой: к ним вернёт Ctrl+Z
        if not self.dup or not event.ctrl:
            _gizmo_press[:] = [time.perf_counter(), event.mouse_x, event.mouse_y]
            return {'PASS_THROUGH'}
        self.axis = handle_axis(context, g)
        if self.axis is None:
            return {'PASS_THROUGH'}      # кольцо, масштаб: штатный Ctrl (шаг)
        self.start = (getattr(event, "mouse_prev_press_x", event.mouse_x), getattr(event, "mouse_prev_press_y", event.mouse_y))
        self.orient = context.scene.transform_orientation_slots[0].type
        self.threshold = DUP_DRAG_PX * context.preferences.system.ui_scale
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not event.ctrl:
            return {'CANCELLED'}      # Ctrl released before duplication: never reuse a previous copy gesture.
        if event.type == 'MOUSEMOVE':
            if math.hypot(event.mouse_x - self.start[0], event.mouse_y - self.start[1]) >= self.threshold:
                return self.start_dup(context)
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            # короткий Ctrl+тык по ручке — это Ctrl+клик (маска по полигруппе / инверсия маски)
            safe(bpy.ops.sculpt_fund.mask_click, 'INVOKE_DEFAULT', filter_type='SMOOTH')
            return {'FINISHED'}
        elif event.type in {'ESC', 'RIGHTMOUSE'}:
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def start_dup(self, context):
        obj = context.active_object
        err = dup_blockers(obj)
        if err:
            self.report({'WARNING'}, err)
            return {'FINISHED'}
        if mesh_readable(obj) and not unmasked_faces(obj.data).any():
            self.report({'INFO'}, "Всё замаскировано: копировать нечего")
            return {'FINISHED'}
        bpy.app.timers.register(functools.partial(
            _run_dup, context.window, context.area, context.region, obj.name, self.axis, self.orient), first_interval=0.0)
        return {'FINISHED'}


_ghost = {"handle": None}


def _draw_ghost(op):
    """Призрак гизмо там, куда переедет центр (настоящее гизмо на время Alt-протяжки спрятано)."""
    try:
        if bpy.context.region != op.region:
            return
        import gpu
        from gpu_extras.batch import batch_for_shader
        rv = op.rv
        c = view3d_utils.location_3d_to_region_2d(op.region, rv, op.p)
        if c is None:
            return
        ui = bpy.context.preferences.system.ui_scale
        size = bpy.context.preferences.view.gizmo_size * ui * 0.9
        th = bpy.context.preferences.themes[0].user_interface
        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("viewportSize", (op.region.width, op.region.height))
        k = rv.view_distance * 0.05
        for i, col in enumerate((th.axis_x, th.axis_y, th.axis_z)):
            e = view3d_utils.location_3d_to_region_2d(op.region, rv, op.p + op.M.col[i] * k)
            if e is None or (e - c).length < 1e-3:
                continue
            d = (e - c).normalized() * size
            shader.uniform_float("lineWidth", 2.5 * ui)
            shader.uniform_float("color", (col[0], col[1], col[2], 0.95))
            batch_for_shader(shader, 'LINES', {"pos": [(c.x, c.y, 0.0), (c.x + d.x, c.y + d.y, 0.0)]}).draw(shader)
        ring = [(c.x + 9 * ui * math.cos(a * math.pi / 12), c.y + 9 * ui * math.sin(a * math.pi / 12), 0.0) for a in range(25)]
        segs = [p for i in range(24) for p in (ring[i], ring[i + 1])]
        shader.uniform_float("lineWidth", 2.0 * ui)
        shader.uniform_float("color", (1.0, 1.0, 1.0, 0.95))
        batch_for_shader(shader, 'LINES', {"pos": segs}).draw(shader)
        gpu.state.blend_set('NONE')
    except (ReferenceError, AttributeError):
        pass


class SCULPTFUND_OT_gizmo_alt(bpy.types.Operator):
    """Alt+протяжка за ручку гизмо — гизмо без меша, как в ZBrush: стрелка — центр по оси, центр — свободно,
    кольцо — поворот осей гизмо"""
    bl_idname = "sculpt_fund.gizmo_alt"
    bl_label = "Move Gizmo Only"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and context.region_data is not None

    def invoke(self, context, event):
        if not alt_held(event):
            return {'PASS_THROUGH'}         # Alt на самом деле отпущен: обычная протяжка ручки, с мешем
        gg, g = xform_gizmo_hit(context)
        if gg is None:
            return {'PASS_THROUGH'}
        self.kind, idx = handle_kind(context, g)
        if self.kind is None:
            return {'PASS_THROUGH'}
        obj = context.active_object
        pivot_store(obj, obj.matrix_world.inverted_safe() @ Vector(gg.gizmos[0].matrix_basis.translation))
        self.region, self.rv = context.region, context.region_data
        self.p0 = obj.matrix_world @ pivot_local(obj)
        self.p = self.p0.copy()
        self.M = orientation_matrix(context)
        self.press = Vector((getattr(event, "mouse_prev_press_x", event.mouse_x) - context.region.x,
                             getattr(event, "mouse_prev_press_y", event.mouse_y) - context.region.y))
        c2d = view3d_utils.location_3d_to_region_2d(self.region, self.rv, self.p0)
        if c2d is None:
            return {'CANCELLED'}
        self.c2d = c2d
        if self.kind in ('ROT', 'ROT_VIEW'):
            slot = context.scene.transform_orientation_slots[0]
            self.prev_slot = slot.type
            self.prev_matrix = slot.custom_orientation.matrix.copy() if slot.custom_orientation else None
            toward = self.rv.view_rotation @ Vector((0.0, 0.0, 1.0))
            self.axis = (self.M.col[idx].normalized() if self.kind == 'ROT' else toward.normalized())
            self.sign = 1.0 if self.axis.dot(toward) >= 0 else -1.0
            v = self.press - self.c2d
            self.a0 = math.atan2(v.y, v.x)
            self.custom = ensure_gizmo_orientation(context, self.M)
            if self.custom is None:
                return {'CANCELLED'}
        else:
            self.axis = self.M.col[idx].normalized() if self.kind == 'AXIS' else None
            self.space = context.space_data
            self.gizmo_shown = self.space.show_gizmo_tool
            self.space.show_gizmo_tool = False
            _pivot["busy"] = True
            _ghost["handle"] = bpy.types.SpaceView3D.draw_handler_add(_draw_ghost, (self,), 'WINDOW', 'POST_PIXEL')
        # видно, что включился режим Alt: если Alt не нажимали — его шлёт кнопка пера / экспресс-клавиша планшета
        context.area.header_text_set("Alt: " + ("поворот осей гизмо" if self.kind in ('ROT', 'ROT_VIEW') else
                                               "гизмо без меша") + "    Esc / ПКМ — отмена")
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def update(self, mouse):
        if self.kind == 'AXIS':
            k = self.rv.view_distance * 0.1
            e = view3d_utils.location_3d_to_region_2d(self.region, self.rv, self.p0 + self.axis * k)
            if e is None or (e - self.c2d).length < 2.0:          # ось смотрит в экран: вдоль неё пером не потянуть
                return
            d = e - self.c2d
            t = (mouse - self.press).dot(d.normalized()) / d.length * k
            self.p = self.p0 + self.axis * t
        elif self.kind == 'FREE':
            target = mouse + (self.c2d - self.press)
            self.p = view3d_utils.region_2d_to_location_3d(self.region, self.rv, target, self.p0)
        else:
            v = mouse - self.c2d
            if v.length < 3.0:
                return
            angle = (math.atan2(v.y, v.x) - self.a0) * self.sign
            self.custom.matrix = Matrix.Rotation(angle, 3, self.axis) @ self.M

    def end_move_ui(self, context):
        if _ghost["handle"] is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_ghost["handle"], 'WINDOW')
            _ghost["handle"] = None
        if getattr(self, "space", None) is not None:
            self.space.show_gizmo_tool = self.gizmo_shown
        _pivot["busy"] = False
        context.area.tag_redraw()

    def modal(self, context, event):
        context.area.tag_redraw()
        if event.type == 'MOUSEMOVE':
            self.update(Vector((event.mouse_region_x, event.mouse_region_y)))
            return {'RUNNING_MODAL'}
        if (event.type == 'LEFTMOUSE' and event.value == 'RELEASE') or event.type in {'ESC', 'RIGHTMOUSE'}:
            context.area.header_text_set(None)
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if self.kind in ('AXIS', 'FREE'):
                self.end_move_ui(context)
                delta = self.p - self.p0
                if delta.length > 1e-9:
                    pivot_only_move(context, delta, self.report)
            else:
                _pivot.pop('auto_orient', None)
                remember_orientation(context)
            return {'FINISHED'}
        elif event.type in {'ESC', 'RIGHTMOUSE'}:
            if self.kind in ('AXIS', 'FREE'):
                self.end_move_ui(context)
            else:
                slot = context.scene.transform_orientation_slots[0]
                if self.prev_matrix is not None and self.custom is not None and self.prev_slot == GIZMO_ORIENT:
                    self.custom.matrix = self.prev_matrix
                slot.type = self.prev_slot
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


# --- масштаб кубиком по повёрнутой оси гизмо ----------------------------------------------------------------
# Штатный масштаб Sculpt хранит его как три множителя по осям объекта (SculptSession.pivot_scale): при осях гизмо,
# повёрнутых относительно объекта (после поворота меша, «ZBrush Gizmo», объект повёрнут в Object Mode), меш
# растягивается вкось. Здесь — точно вдоль оси гизмо, как штатный трансформ: вес вершины 1 − маска, скрытые на месте,
# симметрия меша по областям (как transform_matrices_init) и вершины на плоскости симметрии не сходят с неё.
# Вживую позиции пишутся напрямую; при отпускании один шаг истории: исходные позиции → пустой штатный Resize
# (шаг Sculpt запоминает их) → итоговые позиции. Ctrl+Z / Ctrl+Shift+Z — штатно, проверено t47/t49.
DEFORM_MODIFIERS = {'ARMATURE', 'CAST', 'CURVE', 'DISPLACE', 'HOOK', 'LAPLACIANDEFORM', 'LATTICE', 'MESH_DEFORM',
                    'SHRINKWRAP', 'SIMPLE_DEFORM', 'SMOOTH', 'CORRECTIVE_SMOOTH', 'LAPLACIANSMOOTH',
                    'SURFACE_DEFORM', 'WARP', 'WAVE', 'NODES'}
SYMM_PLANE_EPS = 0.00002    # transform_mirror_max_distance_eps в Blender
_scale_line = {"handle": None}


def axes_follow_object(obj, M):
    """Оси гизмо параллельны осям объекта — штатный масштаб (по осям объекта) и так точен."""
    W = obj.matrix_world.to_3x3()
    axes = [W.col[j].normalized() for j in range(3)]
    return all(max(abs(M.col[i].normalized().dot(a)) for a in axes) > 1.0 - 1e-6 for i in range(3))


def axis_scale_blockers(obj):
    if multires(obj) is not None:
        return "у объекта Multires"
    if obj.data.shape_keys:
        return "у меша есть Shape Keys"
    if obj.use_dynamic_topology_sculpting:
        return "включён Dyntopo"
    if any(m.show_viewport and m.type in DEFORM_MODIFIERS for m in obj.modifiers):
        return "у объекта деформирующие модификаторы"
    return None


def axis_scale_offsets(obj, center_local, axis_world, co=None):
    """Индексы двигаемых вершин, их исходные позиции и смещение на единицу (s − 1): позиция = p + (s − 1)·K.
    Масштаб вдоль оси A мира в координатах объекта: L = W⁻¹(I + (s − 1)AAᵀ)W = I + (s − 1)·u·vᵀ, u = W⁻¹A, v = WᵀA.
    co — исходные позиции (иначе читаются из меша)."""
    import numpy as np
    me = obj.data
    n = len(me.vertices)
    if co is None:
        co = np.empty(n * 3, dtype=np.float32)
        me.attributes["position"].data.foreach_get("vector", co)
        co = co.reshape(n, 3)
    weight = 1.0 - read_attr(me, ".sculpt_mask", n, np.float32, 0.0)
    weight[read_attr(me, ".hide_vert", n, bool, False)] = 0.0
    idx = np.nonzero(weight > 0.0)[0]
    W = np.array(obj.matrix_world.to_3x3(), dtype=np.float64)
    A = np.array(axis_world.normalized(), dtype=np.float64)
    u, v = np.linalg.solve(W, A), W.T @ A
    c = np.array(center_local, dtype=np.float64)
    p = co[idx].astype(np.float64)
    symm = np.array((me.use_mirror_x, me.use_mirror_y, me.use_mirror_z))
    # Область симметрии вершины против области центра: отражённые центр и ось (F·L·F, F·c), F = diag(±1)
    flip = np.where(symm & ((p < 0.0) != (c < 0.0)), -1.0, 1.0)
    k = np.einsum('ij,ij->i', p - flip * c, flip * v) * np.clip(weight[idx], 0.0, 1.0)
    offsets = (flip * u) * k[:, None]
    offsets[symm & (np.abs(p) < SYMM_PLANE_EPS)] = 0.0
    return co, idx, offsets


def _draw_scale_line(op):
    """Линия оси масштаба через центр гизмо (как у штатного трансформа)."""
    try:
        if bpy.context.region != op.region:
            return
        import gpu
        from gpu_extras.batch import batch_for_shader
        c, d = op.c2d, op.dir2d * 10000.0
        ui = bpy.context.preferences.system.ui_scale
        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("viewportSize", (op.region.width, op.region.height))
        shader.uniform_float("lineWidth", 1.5 * ui)
        shader.uniform_float("color", (*op.color, 0.9))
        batch_for_shader(shader, 'LINES', {"pos": [(c.x - d.x, c.y - d.y, 0.0), (c.x + d.x, c.y + d.y, 0.0)]}).draw(shader)
        gpu.state.blend_set('NONE')
    except (ReferenceError, AttributeError):
        pass


class SCULPTFUND_OT_gizmo_scale(bpy.types.Operator):
    """Протяжка кубика масштаба: точно вдоль оси гизмо, даже когда оси повёрнуты относительно объекта
    (Ctrl — шаг 0,1, Shift — точно, Esc — отмена)"""
    bl_idname = "sculpt_fund.gizmo_scale"
    bl_label = "Scale Along Gizmo Axis"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and context.region_data is not None

    def invoke(self, context, event):
        gg, g = xform_gizmo_hit(context)
        if gg is None or g is None or g.bl_idname != 'GIZMO_GT_arrow_3d' or getattr(g, "draw_style", None) != 'BOX':
            return {'PASS_THROUGH'}
        axis = axis_by_color(context, g.color)
        obj = context.active_object
        M = orientation_matrix(context)
        if axis is None or obj is None or obj.type != 'MESH' or axes_follow_object(obj, M):
            return {'PASS_THROUGH'}      # оси гизмо по осям объекта: штатный масштаб точен
        err = axis_scale_blockers(obj)
        if err:
            self.report({'WARNING'}, "Масштаб по повёрнутой оси гизмо недоступен (%s): штатный — по осям объекта" % err)
            return {'PASS_THROUGH'}
        press = Vector((getattr(event, "mouse_prev_press_x", event.mouse_x) - context.region.x,
                        getattr(event, "mouse_prev_press_y", event.mouse_y) - context.region.y))
        res = self.start(context, obj, Vector(gg.gizmos[0].matrix_basis.translation), axis, M.col[axis].normalized(), press)
        if res == {'RUNNING_MODAL'}:
            context.window_manager.modal_handler_add(self)
        return res

    def start(self, context, obj, center, axis, A, press):
        import numpy as np
        pivot_store(obj, obj.matrix_world.inverted_safe() @ center)
        self.co, self.idx, self.offsets = axis_scale_offsets(obj, pivot_local(obj), A)
        if not len(self.idx):
            self.report({'INFO'}, "Всё замаскировано: масштабировать нечего")
            return {'CANCELLED'}
        self.base = self.co[self.idx].astype(np.float64)
        self.buf = self.co.copy()
        self.obj_name, self.axis = obj.name, axis
        self.region, self.rv = context.region, context.region_data
        c2d = view3d_utils.location_3d_to_region_2d(self.region, self.rv, center)
        if c2d is None:
            return {'PASS_THROUGH'}
        self.c2d = c2d
        e = view3d_utils.location_3d_to_region_2d(self.region, self.rv, center + A * self.rv.view_distance * 0.1)
        self.press = press
        self.dir2d = (e - c2d).normalized() if e is not None and (e - c2d).length > 2.0 else (self.press - c2d).normalized()
        self.d0 = (self.press - c2d).dot(self.dir2d)
        if abs(self.d0) < 4.0:
            self.d0 = math.copysign(4.0, self.d0 or 1.0)
        th = context.preferences.themes[0].user_interface
        self.color = tuple((th.axis_x, th.axis_y, th.axis_z)[axis])[:3]
        self.s, self.raw, self.precise = 1.0, 1.0, None
        self.space = context.space_data
        self.gizmo_shown = self.space.show_gizmo_tool
        self.space.show_gizmo_tool = False
        _pivot["busy"] = True
        _scale_line["handle"] = bpy.types.SpaceView3D.draw_handler_add(_draw_scale_line, (self,), 'WINDOW', 'POST_PIXEL')
        self.header(context)
        return {'RUNNING_MODAL'}

    def header(self, context):
        context.area.header_text_set("Масштаб по оси %s гизмо: %.3f    Ctrl — шаг 0,1   Shift — точно   Esc / ПКМ — отмена"
                                     % ("XYZ"[self.axis], self.s))

    def write(self, s):
        obj = bpy.data.objects.get(self.obj_name)
        if obj is None:
            return
        self.buf[self.idx] = self.base + (s - 1.0) * self.offsets
        obj.data.attributes["position"].data.foreach_set("vector", self.buf.ravel())
        obj.data.update()

    def end_ui(self, context):
        if _scale_line["handle"] is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_scale_line["handle"], 'WINDOW')
            _scale_line["handle"] = None
        self.space.show_gizmo_tool = self.gizmo_shown
        _pivot["busy"] = False
        context.area.header_text_set(None)
        context.area.tag_redraw()

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            mouse = Vector((event.mouse_region_x, event.mouse_region_y))
            self.raw = (mouse - self.c2d).dot(self.dir2d) / self.d0
            if event.shift:
                if self.precise is None:
                    self.precise = (self.raw, self.s)
                s = self.precise[1] + (self.raw - self.precise[0]) * 0.1
            else:
                self.precise = None
                s = self.raw
            if event.ctrl:
                s = round(s * 10.0) / 10.0
            if s != self.s:
                self.s = s
                self.write(s)
            self.header(context)
            context.area.tag_redraw()
        elif (event.type == 'LEFTMOUSE' and event.value == 'RELEASE') or event.type in {'RET', 'NUMPAD_ENTER'}:
            self.end_ui(context)
            if abs(self.s - 1.0) < 1e-7:
                self.write(1.0)
                return {'CANCELLED'}
            # Шаг истории: Sculpt запоминает исходные позиции пустым штатным Resize, затем итог.
            self.write(1.0)
            res = safe(bpy.ops.transform.resize, 'EXEC_DEFAULT', True, value=(1.0, 1.0, 1.0),
                       orient_type='GLOBAL', report=self.report)
            if res == {'CANCELLED'}:
                return {'CANCELLED'}        # без шага истории изменение не оставляем
            self.write(self.s)
            return {'FINISHED'}
        elif event.type in {'ESC', 'RIGHTMOUSE'}:
            self.end_ui(context)
            self.write(1.0)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


# S: масштаб, как S в Object Mode, но по осям гизмо. Штатный масштаб Sculpt держит его тремя множителями по осям
# объекта (см. выше): S и затем X / Y / Z тянул по осям объекта (≈ по миру), а не по повёрнутым осям гизмо
# (21.10.2026). Здесь та же запись позиций, что у кубика: вживую напрямую, при подтверждении один шаг истории.
_scale_ui = {"handle": None}


def multi_axis_offsets(obj, center_local, axes_world, co):
    """Смещения на единицу по нескольким взаимно перпендикулярным осям: ось, плоскость или все три (равномерно)."""
    idx, total = None, None
    for axis in axes_world:
        _co, idx, offsets = axis_scale_offsets(obj, center_local, axis, co)
        total = offsets if total is None else total + offsets
    return idx, total


def _draw_scale_ui(op):
    """Пунктир от центра к перу (как у штатного S) и линии осей ограничения."""
    try:
        if bpy.context.region != op.region:
            return
        import gpu
        from gpu_extras.batch import batch_for_shader
        ui = bpy.context.preferences.system.ui_scale
        th = bpy.context.preferences.themes[0].user_interface
        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("viewportSize", (op.region.width, op.region.height))
        c = op.c2d
        for i in op.axes():
            if op.constraint is None:
                break
            e = view3d_utils.location_3d_to_region_2d(op.region, op.rv, op.center + op.M.col[i] * op.rv.view_distance * 0.1)
            if e is None or (e - c).length < 1.0:
                continue
            d = (e - c).normalized() * 10000.0
            col = (th.axis_x, th.axis_y, th.axis_z)[i]
            shader.uniform_float("lineWidth", 1.5 * ui)
            shader.uniform_float("color", (col[0], col[1], col[2], 0.9))
            batch_for_shader(shader, 'LINES', {"pos": [(c.x - d.x, c.y - d.y, 0.0), (c.x + d.x, c.y + d.y, 0.0)]}).draw(shader)
        m = op.mouse
        length = max((m - c).length, 1e-6)
        step = 6.0 * ui
        segs = []
        t = 0.0
        while t < length:
            a, b = c + (m - c) * (t / length), c + (m - c) * (min(t + step, length) / length)
            segs += [(a.x, a.y, 0.0), (b.x, b.y, 0.0)]
            t += step * 2
        if segs:
            shader.uniform_float("lineWidth", 1.0 * ui)
            shader.uniform_float("color", (1.0, 1.0, 1.0, 0.8))
            batch_for_shader(shader, 'LINES', {"pos": segs}).draw(shader)
        gpu.state.blend_set('NONE')
    except (ReferenceError, AttributeError):
        pass


NUM_KEYS = {'ZERO': "0", 'ONE': "1", 'TWO': "2", 'THREE': "3", 'FOUR': "4", 'FIVE': "5", 'SIX': "6", 'SEVEN': "7",
            'EIGHT': "8", 'NINE': "9", 'NUMPAD_0': "0", 'NUMPAD_1': "1", 'NUMPAD_2': "2", 'NUMPAD_3': "3",
            'NUMPAD_4': "4", 'NUMPAD_5': "5", 'NUMPAD_6': "6", 'NUMPAD_7': "7", 'NUMPAD_8': "8", 'NUMPAD_9': "9",
            'PERIOD': ".", 'NUMPAD_PERIOD': ".", 'COMMA': "."}


class SCULPTFUND_OT_scale(bpy.types.Operator):
    """S: масштаб незамаскированного вокруг центра гизмо. X / Y / Z — вдоль оси гизмо (даже повёрнутой), Shift+X / Y / Z —
    в плоскости, та же клавиша ещё раз — снова равномерно. Ctrl — шаг 0,1, Shift — точно, цифры — значение.
    ЛКМ / Enter — готово, ПКМ / Esc — отмена"""
    bl_idname = "sculpt_fund.scale"
    bl_label = "Scale"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and context.region_data is not None

    def invoke(self, context, event):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}
        err = axis_scale_blockers(obj)
        if err:
            # Multires, Dyntopo, Shape Keys, деформирующие модификаторы — штатный масштаб (по осям объекта)
            self.report({'INFO'}, "S по осям гизмо недоступен (%s): штатный масштаб" % err)
            return safe(bpy.ops.transform.resize, 'INVOKE_DEFAULT', report=self.report)
        res = self.start(context, event, obj)
        if res == {'RUNNING_MODAL'}:
            context.window_manager.modal_handler_add(self)
        return res

    def start(self, context, event, obj):
        import numpy as np
        self.obj_name = obj.name
        self.center_local = pivot_local(obj).copy()
        self.center = obj.matrix_world @ self.center_local
        self.M = orientation_matrix(context)
        self.region, self.rv = context.region, context.region_data
        c2d = view3d_utils.location_3d_to_region_2d(self.region, self.rv, self.center)
        if c2d is None:
            return {'CANCELLED'}
        self.c2d = c2d
        self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.d0 = max((self.mouse - c2d).length, 4.0)
        n = len(obj.data.vertices)
        co = np.empty(n * 3, dtype=np.float32)
        obj.data.attributes["position"].data.foreach_get("vector", co)
        self.base_co = co.reshape(n, 3)
        self.constraint = None          # None — равномерно, ('AXIS', i) или ('PLANE', i)
        if not self.prepare():
            self.report({'INFO'}, "Всё замаскировано: масштабировать нечего")
            return {'CANCELLED'}
        self.s, self.precise, self.typed = 1.0, None, ""
        self.space = context.space_data
        self.gizmo_shown = self.space.show_gizmo_tool
        self.space.show_gizmo_tool = False
        _pivot["busy"] = True
        _scale_ui["handle"] = bpy.types.SpaceView3D.draw_handler_add(_draw_scale_ui, (self,), 'WINDOW', 'POST_PIXEL')
        self.header(context)
        return {'RUNNING_MODAL'}

    def axes(self):
        if self.constraint is None:
            return [0, 1, 2]
        kind, i = self.constraint
        return [i] if kind == 'AXIS' else [j for j in range(3) if j != i]

    def prepare(self):
        obj = bpy.data.objects.get(self.obj_name)
        if obj is None:
            return False
        idx, offsets = multi_axis_offsets(obj, self.center_local, [self.M.col[i].normalized() for i in self.axes()],
                                          self.base_co)
        if idx is None or not len(idx):
            return False
        self.idx, self.offsets = idx, offsets
        self.base = self.base_co[idx].astype('float64')
        self.buf = self.base_co.copy()
        return True

    def header(self, context):
        if self.constraint is None:
            what = "равномерно"
        else:
            kind, i = self.constraint
            what = ("по оси " if kind == 'AXIS' else "в плоскости без ") + "XYZ"[i] + " гизмо"
        value = self.typed + "_" if self.typed else "%.3f" % self.s
        context.area.header_text_set("Масштаб %s: %s    X / Y / Z — ось, Shift+ось — плоскость   Ctrl — шаг 0,1   "
                                     "Shift — точно   ЛКМ / Enter — готово   ПКМ / Esc — отмена" % (what, value))

    def write(self, s):
        obj = bpy.data.objects.get(self.obj_name)
        if obj is None:
            return
        self.buf[self.idx] = self.base + (s - 1.0) * self.offsets
        obj.data.attributes["position"].data.foreach_set("vector", self.buf.ravel())
        obj.data.update()

    def update(self, context, event):
        if self.typed:
            try:
                s = float(self.typed)
            except ValueError:
                s = self.s
        else:
            raw = (self.mouse - self.c2d).length / self.d0
            if event.shift:
                if self.precise is None:
                    self.precise = (raw, self.s if self.s is not None else raw)
                s = self.precise[1] + (raw - self.precise[0]) * 0.1
            else:
                self.precise = None
                s = raw
            if event.ctrl:
                s = round(s * 10.0) / 10.0
        if s != self.s:
            self.s = s
            self.write(s)
        self.header(context)
        context.area.tag_redraw()

    def end_ui(self, context):
        if _scale_ui["handle"] is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_scale_ui["handle"], 'WINDOW')
            _scale_ui["handle"] = None
        self.space.show_gizmo_tool = self.gizmo_shown
        _pivot["busy"] = False
        context.area.header_text_set(None)
        context.area.tag_redraw()

    def modal(self, context, event):
        t, v = event.type, event.value
        if t == 'MOUSEMOVE':
            self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
            self.update(context, event)
        elif t in {'X', 'Y', 'Z'} and v == 'PRESS':
            new = ('PLANE' if event.shift else 'AXIS', "XYZ".index(t))
            previous = self.constraint
            self.constraint = None if self.constraint == new else new
            self.write(1.0)
            if not self.prepare():
                self.constraint = previous
                self.prepare()
            self.s = None
            self.update(context, event)
        elif t in NUM_KEYS and v == 'PRESS':
            self.typed += NUM_KEYS[t]
            self.update(context, event)
        elif t in {'MINUS', 'NUMPAD_MINUS'} and v == 'PRESS':
            self.typed = self.typed[1:] if self.typed.startswith("-") else "-" + self.typed
            self.update(context, event)
        elif t == 'BACK_SPACE' and v == 'PRESS':
            self.typed = self.typed[:-1]
            self.update(context, event)
        elif t in {'LEFT_CTRL', 'RIGHT_CTRL', 'LEFT_SHIFT', 'RIGHT_SHIFT'}:
            self.update(context, event)
        elif (t == 'LEFTMOUSE' and v == 'PRESS') or (t in {'RET', 'NUMPAD_ENTER', 'SPACE'} and v == 'PRESS'):
            return self.confirm(context)
        elif t in {'RIGHTMOUSE', 'ESC'} and v == 'PRESS':
            self.end_ui(context)
            self.write(1.0)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def confirm(self, context):
        self.end_ui(context)
        s = self.s if self.s is not None else 1.0
        self.write(1.0)
        if abs(s - 1.0) < 1e-7:
            return {'CANCELLED'}
        # Шаг истории, как у кубика: Sculpt запоминает исходные позиции пустым штатным Resize, затем итог
        if safe(bpy.ops.transform.resize, 'EXEC_DEFAULT', True, value=(1.0, 1.0, 1.0), orient_type='GLOBAL',
                report=self.report) == {'CANCELLED'}:
            return {'CANCELLED'}
        self.write(s)
        return {'FINISHED'}


# Grab (3), как Move в ZBrush, — свой (27.10.2026). Штатный Grab с Falloff Projected цеплял меш и с фона, но его
# «труба» вдоль взгляда тянула и всё за точкой нажатия — другую сторону, места выше / ниже («как будто несколько
# грабов»), а Front Faces Only смотрит на камеру, не на протяжку: плоский кубик сбоку не утолщался. Здесь — сфера
# радиуса кисти вокруг точки на поверхности (мимо меша — ближайшая вершина в круге кисти), кривая спада, Hardness и
# сила кисти, маска, скрытое, симметрия меша (X / Y / Z); BackfaceMask (Front Faces Only кисти) — по направлению
# протяжки: двигается то, что смотрит туда, куда тянешь (тянешь вниз — едет низ, верх стоит). Запись позиций — как у S
# (1,4 мс на шаг на 431 тыс. вершин); шаг истории — пустой штатный Resize и итог. Dyntopo / Multires / Shape Keys /
# деформирующие модификаторы — штатный Grab.
GRAB_CURVES = {
    'SMOOTH': lambda q: 3 * q * q - 2 * q ** 3,
    'SMOOTHER': lambda q: q ** 3 * (q * (q * 6 - 15) + 10),
    'SHARP': lambda q: q * q,
    'LIN': lambda q: q,
    'ROOT': lambda q: q ** 0.5,
    'CONSTANT': lambda q: q * 0 + 1,
    'SPHERE': lambda q: (2 * q - q * q) ** 0.5,
    'POW4': lambda q: q ** 4,
    'INVSQUARE': lambda q: q * (2 - q),
}


def brush_falloff(brush):
    """Спад кисти f(расстояние 0…1) (как BKE_brush_curve_strength) с учётом Hardness. Непрерывный: пресеты — формулой,
    свою кривую — линейно между 1025 точками (1.5.1 брал ступени таблицы на 257 точек — при большой протяжке на густом
    меше они проступали концентрическими кольцами)."""
    import numpy as np
    hard = min(max(getattr(brush, "hardness", 0.0), 0.0), 0.999)
    preset = getattr(brush, "curve_distance_falloff_preset", 'SMOOTH')
    curve = GRAB_CURVES.get(preset, GRAB_CURVES['SMOOTH'])
    if preset == 'CUSTOM':
        try:
            cm = brush.curve_distance_falloff
            cm.initialize()
            xs = np.linspace(0.0, 1.0, 1025)
            ys = np.array([cm.evaluate(cm.curves[0], float(x)) for x in xs])
            curve = lambda q: np.interp(1.0 - q, xs, ys)    # noqa: E731 — кривая Blender задана от центра (0) к краю
        except (AttributeError, RuntimeError, TypeError):
            curve = GRAB_CURVES['SMOOTH']

    def falloff(dist):
        p = np.clip((np.asarray(dist, dtype=np.float64) - hard) / (1.0 - hard), 0.0, 1.0)
        return np.clip(np.where(p < 1.0, curve(1.0 - p), 0.0), 0.0, 1.0)
    return falloff


def brush_radius_px(context, brush):
    """Радиус кисти в пикселях вида: Size в Blender 5.2 — диаметр."""
    ups = context.tool_settings.sculpt.unified_paint_settings
    size = ups.size if getattr(ups, "use_unified_size", False) else brush.size
    return max(size * 0.5 * context.preferences.system.ui_scale, 1.0)


def zb_grab_wanted(context):
    if not prefs().controls_on or not brush_tool_active(context):
        return False
    brush = context.tool_settings.sculpt.brush
    obj = context.active_object
    return (brush is not None and getattr(brush, "sculpt_brush_type", None) == 'GRAB' and obj is not None
            and obj.type == 'MESH' and len(obj.data.vertices) > 0 and axis_scale_blockers(obj) is None)


def mirror_flips(me):
    """Множители координат для проходов симметрии меша: (1,1,1) и зеркала по включённым осям и их сочетаниям."""
    import numpy as np
    flips = [np.ones(3)]
    for i, on in enumerate((me.use_mirror_x, me.use_mirror_y, me.use_mirror_z)):
        if on:
            flips += [f * np.where(np.arange(3) == i, -1.0, 1.0) for f in flips]
    return flips


class SCULPTFUND_OT_zb_grab(bpy.types.Operator):
    """Grab как Move в ZBrush: сфера радиуса кисти у точки нажатия (мимо меша — ближайшая вершина в круге кисти);
    с BackfaceMask двигается только то, что смотрит в сторону протяжки"""
    bl_idname = "sculpt_fund.zb_grab"
    bl_label = "Grab (ZBrush Move)"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and context.region_data is not None

    def invoke(self, context, event):
        if not zb_grab_wanted(context):
            return {'PASS_THROUGH'}
        lmb_nav = not prefs().disable_lmb_navigation
        if lmb_nav and not depth_hit(context, event):
            return {'PASS_THROUGH'}         # пустой фон при навигации ЛКМ — вращение вида
        res = self.start(context, Vector((event.mouse_region_x, event.mouse_region_y)), depth_point(context, event, context.active_object))
        if res == {'RUNNING_MODAL'}:
            context.window_manager.modal_handler_add(self)
        elif res == {'CANCELLED'} and lmb_nav:
            return {'PASS_THROUGH'}
        return res

    def start(self, context, mouse, hit):
        """hit — точка поверхности под пером (мир) или None (мимо меша)."""
        import numpy as np
        obj = context.active_object
        brush = context.tool_settings.sculpt.brush
        region, rv = context.region, context.region_data
        rpx = brush_radius_px(context, brush)
        me = obj.data
        n = len(me.vertices)
        co = np.empty(n * 3, np.float32)
        me.attributes["position"].data.foreach_get("vector", co)
        co = co.reshape(n, 3)
        W = np.array(obj.matrix_world, dtype=np.float64)
        hide = read_attr(me, ".hide_vert", n, bool, False)
        if hit is None:
            # мимо меша: ближайшая к перу видимая вершина в круге кисти (как Move в ZBrush)
            world = co.astype(np.float64) @ W[:3, :3].T + W[:3, 3]
            h = np.c_[world, np.ones(n)] @ np.array(rv.perspective_matrix, dtype=np.float64).T
            w = h[:, 3]
            front = (w > 1e-6) & ~hide
            ws = np.where(front, w, 1.0)
            sx = (h[:, 0] / ws + 1.0) * 0.5 * region.width
            sy = (h[:, 1] / ws + 1.0) * 0.5 * region.height
            d2 = np.where(front, (sx - mouse.x) ** 2 + (sy - mouse.y) ** 2, np.inf)
            near = np.nonzero(d2 <= rpx * rpx)[0]
            if not len(near):
                return {'CANCELLED'}
            # из попавших в круг — передняя поверхность (ближе к камере), среди неё ближайшая к перу
            depth = w[near]
            cut = depth.min() + (depth.max() - depth.min()) * 0.25 + 1e-9
            front_set = near[depth <= cut]
            hit = Vector(world[front_set[np.argmin(d2[front_set])]].tolist())
        edge = view3d_utils.region_2d_to_location_3d(region, rv, mouse + Vector((rpx, 0.0)), hit)
        center = view3d_utils.region_2d_to_location_3d(region, rv, mouse, hit)
        scale = float(np.cbrt(abs(np.linalg.det(W[:3, :3])))) or 1.0
        r_local = (edge - center).length / scale
        if r_local <= 0.0:
            return {'CANCELLED'}
        inv = obj.matrix_world.inverted_safe()
        anchor = np.array((inv @ hit)[:], dtype=np.float64)
        falloff = brush_falloff(brush)
        keep = (1.0 - read_attr(me, ".sculpt_mask", n, np.float32, 0.0)).astype(np.float64)
        keep[hide] = 0.0
        nor = np.empty(n * 3, np.float32)
        me.vertex_normals.foreach_get("vector", nor)
        nor = nor.reshape(n, 3)
        co64 = co.astype(np.float64)
        self.passes = []
        total = np.zeros(n, np.float64)
        peak = np.zeros(n, np.float64)
        for f in mirror_flips(me):
            d = np.linalg.norm(co64 - anchor * f, axis=1)
            idx = np.nonzero(d < r_local)[0]
            if not len(idx):
                continue
            fac = falloff(d[idx] / r_local) * keep[idx] * brush.strength
            ok = fac > 0.0
            if not ok.any():
                continue
            idx, fac = idx[ok], fac[ok]
            total[idx] += fac
            peak[idx] = np.maximum(peak[idx], fac)
            self.passes.append((f, idx, fac, nor[idx].astype(np.float64)))
        if not self.passes:
            return {'CANCELLED'}
        # там, где сферы симметрии перекрываются, проходы делят смещение плавно (сильнейший / сумма): на плоскости
        # зеркала — пополам, без удвоения, а на краю чужой сферы множитель → 1. В 1.5.1 делилось на число проходов —
        # на границе зеркальной сферы смещение скачком падало вдвое (дуга-кольцо)
        self.norm = np.where(total > 0.0, peak / np.maximum(total, 1e-30), 1.0)
        self.backface = bool(getattr(brush, "use_frontface", False))
        self.obj_name, self.region, self.rv, self.area = obj.name, region, rv, context.area
        self.hit, self.mouse0 = hit, mouse.copy()
        self.to_local = np.array(inv.to_3x3(), dtype=np.float64)
        self.base = co.copy()
        self.buf = co.copy()
        self.delta = Vector()
        self.moved = False
        return {'RUNNING_MODAL'}

    def write(self, delta_world):
        import numpy as np
        obj = bpy.data.objects.get(self.obj_name)
        if obj is None:
            return
        dl = self.to_local @ np.array(delta_world[:], dtype=np.float64)
        length = float(np.linalg.norm(dl))
        disp = np.zeros((len(self.base), 3), np.float64)
        for f, idx, fac, nor in self.passes:
            d = dl * f                              # смещение в зеркальном проходе
            w = fac
            if self.backface and length > 1e-12:
                # BackfaceMask по протяжке: вершина едет, если её нормаль смотрит туда, куда тянешь
                w = fac * np.clip(nor @ (d / length), 0.0, 1.0)
            disp[idx] += w[:, None] * d
        disp *= self.norm[:, None]
        self.buf[:] = self.base + disp.astype(np.float32)
        obj.data.attributes["position"].data.foreach_set("vector", self.buf.ravel())
        obj.data.update()

    def restore(self):
        obj = bpy.data.objects.get(self.obj_name)
        if obj is not None:
            obj.data.attributes["position"].data.foreach_set("vector", self.base.ravel())
            obj.data.update()

    def drag(self, mouse):
        a = view3d_utils.region_2d_to_location_3d(self.region, self.rv, self.mouse0, self.hit)
        b = view3d_utils.region_2d_to_location_3d(self.region, self.rv, mouse, self.hit)
        self.delta = b - a
        self.moved = True
        self.write(self.delta)

    def modal(self, context, event):
        t, v = event.type, event.value
        if t == 'MOUSEMOVE':
            try:
                mouse = Vector((event.mouse_x - self.region.x, event.mouse_y - self.region.y))
            except ReferenceError:
                return self.confirm(context)
            self.drag(mouse)
            try:
                self.area.tag_redraw()
            except ReferenceError:
                pass
        elif t == 'LEFTMOUSE' and v == 'RELEASE':
            return self.confirm(context)
        elif t in {'ESC', 'RIGHTMOUSE'} and v == 'PRESS':
            self.restore()
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def confirm(self, context):
        if not self.moved or self.delta.length < 1e-12:
            self.restore()
            return {'CANCELLED'}
        # Шаг истории, как у S: Sculpt запоминает исходные позиции пустым штатным Resize, затем итог
        self.restore()
        if safe(bpy.ops.transform.resize, 'EXEC_DEFAULT', True, value=(1.0, 1.0, 1.0), orient_type='GLOBAL',
                report=self.report) == {'CANCELLED'}:
            return {'CANCELLED'}
        self.write(self.delta)
        return {'FINISHED'}


def unmasked_faces(me):
    """Видимые грани, у которых все вершины не замаскированы (маска < 0,5)."""
    import numpy as np
    nv, nf = len(me.vertices), len(me.polygons)
    if nf == 0:
        return np.zeros(0, dtype=bool)
    mask = read_attr(me, ".sculpt_mask", nv, np.float32, 0.0)
    starts = np.empty(nf, dtype=np.int64)
    me.polygons.foreach_get("loop_start", starts)
    cv = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", cv)
    ok = np.logical_and.reduceat(mask[cv] < 0.5, starts)
    return ok & ~read_attr(me, ".hide_poly", nf, bool, False)


def split_unmasked(me):
    """Незамаскированные видимые грани по кускам: (целые отдельные куски, вырезы из меша) — индексы граней.
    Связность по общим вершинам, union-find на numpy (без цикла по граням в Python)."""
    import numpy as np
    nv, nf = len(me.vertices), len(me.polygons)
    sel = unmasked_faces(me)
    starts = np.empty(nf, dtype=np.int64)
    me.polygons.foreach_get("loop_start", starts)
    totals = np.empty(nf, dtype=np.int64)
    me.polygons.foreach_get("loop_total", totals)
    cv = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", cv)
    face_of = np.repeat(np.arange(nf), totals)
    sel_c = sel[face_of]
    touch_rest = np.zeros(nv, dtype=bool)
    touch_rest[cv[~sel_c]] = True                    # вершины, которые есть и у остального меша (или скрытого)
    a = cv[sel_c]
    b = cv[starts][face_of][sel_c]                    # каждая вершина грани связана с первой вершиной грани
    parent = np.arange(nv)
    while True:
        pa, pb = parent[a], parent[b]
        if not (pa != pb).any():
            break
        lo = np.minimum(pa, pb)
        np.minimum.at(parent, pa, lo)
        np.minimum.at(parent, pb, lo)
        while True:
            pp = parent[parent]
            if (pp == parent).all():
                break
            parent = pp
    cut_root = np.zeros(nv, dtype=bool)
    cut_root[parent[a[touch_rest[a]]]] = True
    face_root = parent[cv[starts]]
    cut = sel & cut_root[face_root]
    return np.nonzero(sel & ~cut)[0], np.nonzero(cut)[0]


class SCULPTFUND_OT_dup_unmasked(bpy.types.Operator):
    """Внутренний шаг Ctrl+протяжки гизмо (Object Mode): копия незамаскированного внутри объекта; вырез из меша —
    выдавливание со стенками. Старое маскируется, новое остаётся без маски"""
    bl_idname = "sculpt_fund.dup_unmasked"
    bl_label = "Duplicate Unmasked"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'OBJECT'

    def execute(self, context):
        import numpy as np
        obj = context.active_object
        err = dup_blockers(obj)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        me = obj.data
        loose, cut = split_unmasked(me)
        if len(loose) == 0 and len(cut) == 0:
            self.report({'INFO'}, "Всё замаскировано: копировать нечего")
            return {'CANCELLED'}
        new_set = fresh_face_set_id(me)
        bm = bmesh.new()
        bm.from_mesh(me)
        face_sets = bm.faces.layers.int.get(".sculpt_face_set")
        if face_sets is None:
            face_sets = bm.faces.layers.int.new(".sculpt_face_set")
            for face in bm.faces:
                face[face_sets] = 1
        original_faces = set(bm.faces)
        bm.faces.ensure_lookup_table()
        loose_faces = [bm.faces[i] for i in loose]      # до операций: после них индексная таблица устаревает
        faces = [bm.faces[i] for i in cut]
        new_verts = []
        if loose_faces:
            res = bmesh.ops.duplicate(bm, geom=loose_faces)
            new_verts += [e for e in res["geom"] if isinstance(e, bmesh.types.BMVert)]
        if faces:
            res = bmesh.ops.extrude_face_region(bm, geom=faces)
            new_verts += [e for e in res["geom"] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.delete(bm, geom=faces, context='FACES')
        # One fresh group for the duplicate, including any extrusion walls.
        for face in bm.faces:
            if face not in original_faces:
                face[face_sets] = new_set
        bm.verts.index_update()
        new_idx = np.array([v.index for v in new_verts], dtype=np.int64)
        bm.to_mesh(me)
        bm.free()
        attr = me.attributes.get(".sculpt_mask") or me.attributes.new(".sculpt_mask", 'FLOAT', 'POINT')
        mask = np.ones(len(me.vertices), dtype=np.float32)
        mask[new_idx] = 0.0
        attr.data.foreach_set("value", mask)
        me.update()
        return {'FINISHED'}


def _run_dup(window, area, region, obj_name, axis, orient):
    """Таймер Ctrl+протяжки гизмо: шаги истории как действия пользователя (смена режима внутри UNDO-оператора
    ломает историю Sculpt Mode, см. _run_replace). Симметрия на время переноса копии выключается: иначе Blender
    зеркалит перенос относительно центра на другой стороне."""
    try:
        obj = bpy.data.objects.get(obj_name)
        if obj is None or bpy.context.view_layer.objects.active != obj:
            return None
        with bpy.context.temp_override(window=window, area=area, region=region):
            scene = bpy.context.scene
            try:
                mark_inner_steps(scene, True)
                bpy.ops.object.mode_set('EXEC_DEFAULT', True, mode='OBJECT')
                try:
                    res = bpy.ops.sculpt_fund.dup_unmasked('EXEC_DEFAULT', True)
                except RuntimeError as e:
                    print("Sculpt Fund: gizmo duplicate:", e)
                    res = {'CANCELLED'}
                mark_inner_steps(scene, False)
                bpy.ops.object.mode_set('EXEC_DEFAULT', True, mode='SCULPT')     # назад в скульпт в любом случае
            finally:
                mark_inner_steps(scene, False)
            if res != {'FINISHED'}:
                return None
            _pivot["co"] = None     # новый сеанс Sculpt Mode
            set_pivot_unmasked(bpy.context)
            bpy.ops.sculpt_fund.dup_move('INVOKE_DEFAULT', axis=axis)
    except (RuntimeError, ReferenceError, TypeError) as e:
        print("Sculpt Fund: gizmo duplicate:", e)
    return None


# Перенос копии — свой, запись позиций, как у S. Штатный TRANSFORM_OT_translate, запущенный из таймера, брал
# устаревшее положение пера (копия прыгала на всё, что перо прошло за смену режимов) и «кнопкой запуска» —
# движение мыши, а не ЛКМ: отпускание пера его не подтверждало, копия ехала за пером до следующего касания
# («улетает в стратосферу», 22.10.2026). Здесь перенос начинается с первого движения пера, готово — отпускание.
class SCULPTFUND_OT_dup_move(bpy.types.Operator):
    """Внутренний шаг Ctrl+протяжки гизмо: копия едет за пером вдоль стрелки (центр — свободно).
    Отпустить перо / Enter — готово, Esc / ПКМ — копия остаётся на месте"""
    bl_idname = "sculpt_fund.dup_move"
    bl_label = "Move Copy"
    bl_options = {'INTERNAL'}

    axis: IntProperty(default=-1, options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and context.region_data is not None

    def invoke(self, context, event):
        import numpy as np
        obj = context.active_object
        if obj is None or obj.type != 'MESH' or not mesh_readable(obj):
            return {'CANCELLED'}
        me = obj.data
        n = len(me.vertices)
        co = np.empty(n * 3, dtype=np.float32)
        me.attributes["position"].data.foreach_get("vector", co)
        self.buf = co.reshape(n, 3)
        self.idx = np.nonzero(read_attr(me, ".sculpt_mask", n, np.float32, 0.0) < 0.5)[0]
        if not len(self.idx):
            return {'CANCELLED'}
        self.base = self.buf[self.idx].copy()
        self.obj_name = obj.name
        self.center_local = pivot_local(obj).copy()
        self.center = obj.matrix_world @ self.center_local
        self.to_local = obj.matrix_world.to_3x3().inverted_safe()
        self.A = orientation_matrix(context).col[self.axis].normalized() if 0 <= self.axis < 3 else None
        self.area, self.region, self.rv = context.area, context.region, context.region_data
        self.start = None           # точка на оси / в плоскости вида под пером при первом движении
        self.delta = Vector()
        self.space = context.space_data
        self.gizmo_shown = self.space.show_gizmo_tool
        self.space.show_gizmo_tool = False
        _pivot["busy"] = True
        self.area.header_text_set("Копия: %s    Отпустить перо / Enter — готово   Esc / ПКМ — оставить на месте"
                                     % ("по оси %s гизмо" % "XYZ"[self.axis] if self.A is not None else "свободно"))
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def point(self, mouse):
        """Мировая точка под пером: на оси стрелки (ближайшая к лучу вида) или в плоскости вида через центр."""
        origin = view3d_utils.region_2d_to_origin_3d(self.region, self.rv, mouse)
        ray = view3d_utils.region_2d_to_vector_3d(self.region, self.rv, mouse)
        if self.A is not None and abs(ray.normalized().dot(self.A)) < 0.98:
            hit = intersect_line_line(origin, origin + ray, self.center, self.center + self.A)
            if hit is not None:
                return self.center + self.A * (hit[1] - self.center).dot(self.A)
        p = view3d_utils.region_2d_to_location_3d(self.region, self.rv, mouse, self.center)
        if self.A is not None:      # ось почти вдоль взгляда: по экранной проекции, без улёта в бесконечность
            return self.center + self.A * (p - self.center).dot(self.A)
        return p

    def write(self, delta):
        obj = bpy.data.objects.get(self.obj_name)
        if obj is None:
            return
        d = self.to_local @ delta
        self.buf[self.idx] = self.base + (d.x, d.y, d.z)
        obj.data.attributes["position"].data.foreach_set("vector", self.buf.ravel())
        obj.data.update()

    def end_ui(self, context):
        _pivot["busy"] = False
        try:        # перо могло уйти в другую область окна: своя область, а не context.area
            self.space.show_gizmo_tool = self.gizmo_shown
            self.area.header_text_set(None)
            self.area.tag_redraw()
        except (ReferenceError, AttributeError):
            pass

    def modal(self, context, event):
        if getattr(self, "done", False):
            return {'FINISHED'}         # уже готово / отменено: больше ничего не двигать
        t, v = event.type, event.value
        if t == 'MOUSEMOVE':
            try:
                mouse = Vector((event.mouse_x - self.region.x, event.mouse_y - self.region.y))
            except ReferenceError:
                return self.confirm(context)
            p = self.point(mouse)
            if self.start is None:
                self.start = p
            else:
                self.delta = p - self.start
                self.write(self.delta)
                self.area.tag_redraw()
        elif (t == 'LEFTMOUSE' and v in {'RELEASE', 'PRESS'}) or (t in {'RET', 'NUMPAD_ENTER', 'SPACE'} and v == 'PRESS'):
            return self.confirm(context)
        elif t in {'RIGHTMOUSE', 'ESC'} and v == 'PRESS':
            self.done = True
            self.end_ui(context)
            self.write(Vector())
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def confirm(self, context):
        self.done = True
        self.end_ui(context)
        delta = self.delta
        self.write(Vector())
        if delta.length < 1e-9:
            return {'CANCELLED'}
        # Шаг истории, как у S: Sculpt запоминает исходные позиции пустым штатным Resize, затем итог
        if safe(bpy.ops.transform.resize, 'EXEC_DEFAULT', True, value=(1.0, 1.0, 1.0), orient_type='GLOBAL',
                report=self.report) == {'CANCELLED'}:
            return {'CANCELLED'}
        self.write(delta)
        obj = bpy.data.objects.get(self.obj_name)
        if obj is not None:
            set_pivot_unmasked(context)     # гизмо — на копию
        return {'FINISHED'}


ICON_ROW = (    # ряд иконок над гизмо, как в ZBrush: Customize, центр незамаскированного, оси по миру
    # Customize — сразу окно параметров (выбор примитива + OK): меню выбирало бы первый пункт отпусканием пера
    ('PREFERENCES', "sculpt_fund.replace_primitive", {}),
    ('PIVOT_MEDIAN', "sculpt_fund.pivot_unmasked", {}),
    ('ORIENTATION_GLOBAL', "sculpt_fund.gizmo_world", {}),
)


class SCULPTFUND_GGT_gizmo_icons(bpy.types.GizmoGroup):
    bl_idname = "SCULPTFUND_GGT_gizmo_icons"
    bl_label = "Sculpt Fund: Gizmo Icons"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'SCULPT':
            _pivot["co"] = None         # новый сеанс Sculpt Mode начнётся с центром в начале координат объекта
            return False
        space = context.space_data
        gizmo = gizmo_tool_active(context)
        if not gizmo:
            _pivot["alt"] = None        # вне режима гизмо (кисть и т.д.) Ctrl+Z отменяет уже другие действия
        return (prefs().controls_on and space is not None and space.type == 'VIEW_3D' and space.show_gizmo_tool
                and gizmo)

    def setup(self, context):
        self.buttons = []
        for icon, op, props in ICON_ROW:
            g = self.gizmos.new("GIZMO_GT_button_2d")
            g.icon = icon
            g.draw_options = {'BACKDROP', 'OUTLINE'}
            g.color = (0.12, 0.12, 0.12)
            g.alpha = 0.65
            g.color_highlight = (0.4, 0.4, 0.4)
            g.alpha_highlight = 0.9
            g.scale_basis = 13.0
            p = g.target_set_operator(op)
            for k, v in props.items():
                setattr(p, k, v)
            self.buttons.append(g)

    def draw_prepare(self, context):
        pos = pivot_screen(context)
        ui = context.preferences.system.ui_scale
        step = 30.0 * ui
        lift = context.preferences.view.gizmo_size * ui * GIZMO_ICON_LIFT
        for i, g in enumerate(self.buttons):
            g.hide = pos is None
            if pos is not None:
                g.matrix_basis[0][3] = pos.x + step * (i - (len(self.buttons) - 1) / 2)
                g.matrix_basis[1][3] = pos.y + lift


class SCULPTFUND_MT_polygroups_pie(bpy.types.Menu):
    bl_label = "Полигруппы"
    bl_idname = "SCULPTFUND_MT_polygroups_pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("sculpt.face_sets_init", text="Auto Groups").mode = 'LOOSE_PARTS'           # W
        pie.operator("sculpt.face_sets_init", text="Group by Normals").mode = 'NORMALS'           # E
        pie.operator("paint.visibility_invert", text="Invert Visible")                           # S
        pie.operator("sculpt.face_sets_create", text="Group Visible").mode = 'VISIBLE'            # N
        pie.operator("sculpt.face_sets_create", text="Group Masked").mode = 'MASKED'              # NW
        pie.operator("paint.hide_show_all", text="Show All").action = 'SHOW'                      # NE


class SCULPTFUND_MT_primitive_pie(bpy.types.Menu):
    """Shift+A: примитивы, отделение маски и Merge Down"""
    bl_label = "Объекты"
    bl_idname = "SCULPTFUND_MT_primitive_pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        add = SCULPTFUND_OT_add_primitive.bl_idname
        # 8 направлений пирога (W, E, S, N, NW, NE, SW, SE): «Отделить» и Merge Down — каждый в своём (22.10.2026),
        # поэтому редкие в скульпте Torus и Plane делят одно направление
        for key, name, icon in PRIMITIVES[:5]:
            pie.operator(add, text=name, icon=icon).primitive = key
        col = pie.column(align=True)
        for key, name, icon in PRIMITIVES[5:]:
            col.operator(add, text=name, icon=icon).primitive = key
        pie.operator(SCULPTFUND_OT_split_masked.bl_idname, icon='MOD_MASK')
        target, _reason = merge_down_plan(context)
        label = "Merge Down" + (" → " + target.name if target else "")
        pie.operator(SCULPTFUND_OT_merge_down.bl_idname, text=label, icon='AUTOMERGE_ON')


class SCULPTFUND_MT_primitive_menu(bpy.types.Menu):
    bl_label = "Customize"
    bl_idname = "SCULPTFUND_MT_primitive_menu"

    def draw(self, context):
        for key, name, icon in PRIMITIVES:
            self.layout.operator(SCULPTFUND_OT_replace_primitive.bl_idname, text=name, icon=icon).primitive = key


class SCULPTFUND_MT_cs_pie(bpy.types.Menu):
    bl_label = "Ctrl+Shift"
    bl_idname = "SCULPTFUND_MT_cs_pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        cur = prefs().cs_tool
        for key, name, _desc, _op in CS_TOOLS:
            pie.operator(SCULPTFUND_OT_set_cs_tool.bl_idname, text=name,
                         icon='CHECKMARK' if key == cur else 'NONE').tool = key


class SCULPTFUND_MT_ctrl_pie(bpy.types.Menu):
    bl_label = "Ctrl: маска"
    bl_idname = "SCULPTFUND_MT_ctrl_pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        cur = prefs().ctrl_bg_tool
        for key, name, _desc, _short in CTRL_TOOLS:
            pie.operator(SCULPTFUND_OT_set_ctrl_tool.bl_idname, text=name,
                         icon='CHECKMARK' if key == cur else 'NONE').tool = key


class SCULPTFUND_MT_ctrl_menu(bpy.types.Menu):
    bl_label = "Ctrl с пустого места (по мешу — кисть маски)"
    bl_idname = "SCULPTFUND_MT_ctrl_menu"

    def draw(self, context):
        for key, name, desc, _short in CTRL_TOOLS:
            self.layout.operator(SCULPTFUND_OT_set_ctrl_tool.bl_idname, text=name).tool = key


class SCULPTFUND_MT_cs_menu(bpy.types.Menu):
    bl_label = "Ctrl+Shift"
    bl_idname = "SCULPTFUND_MT_cs_menu"

    def draw(self, context):
        for key, name, desc, _op in CS_TOOLS:
            self.layout.operator(SCULPTFUND_OT_set_cs_tool.bl_idname, text=name).tool = key


# --- затемнение других объектов в Sculpt ---------------------------------------------------------------------
# Штатное Fade Inactive Geometry смешивает другие объекты с цветом фона темы: у темы с цветным фоном они не темнели,
# а окрашивались («синее», 21.10.2026). Здесь — нейтрально: поверх них ещё раз полупрозрачный чёрный с тестом глубины
# (заслонённое скульптируемым объектом не темнеет). Геометрия объекта попадает в буфер GPU один раз и обновляется,
# только когда объект меняется; на кадр — по одному вызову рисования на объект. Не вышло (GPU без своих шейдеров) —
# штатное затемнение.
_dim = {"handle": None, "shader": None, "batches": {}, "failed": False}
DIM_DEPTH_BIAS = 2e-6       # сдвиг к камере в NDC (~десяток шагов буфера глубины): слой не мерцает на поверхности


def dim_shader():
    if _dim["shader"] is None:
        import gpu
        info = gpu.types.GPUShaderCreateInfo()
        info.push_constant('MAT4', "mvp")
        info.push_constant('VEC4', "color")
        info.push_constant('FLOAT', "bias")
        info.vertex_in(0, 'VEC3', "pos")
        info.fragment_out(0, 'VEC4', "fragColor")
        info.vertex_source("void main() { gl_Position = mvp * vec4(pos, 1.0); "
                           "gl_Position.z -= bias * gl_Position.w; }")
        info.fragment_source("void main() { fragColor = color; }")
        _dim["shader"] = gpu.shader.create_from_info(info)
    return _dim["shader"]


def dim_batch(obj_eval):
    """Буфер GPU треугольников объекта (вычисленная геометрия, с модификаторами), из кэша, пока объект не менялся."""
    import numpy as np
    from gpu_extras.batch import batch_for_shader
    me = obj_eval.data
    sig = (len(me.vertices), len(me.loop_triangles))
    entry = _dim["batches"].get(obj_eval.name)
    if entry is not None and entry[0] == sig:
        return entry[2]
    n, nt = sig
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    tris = np.empty(nt * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("vertices", tris)
    batch = batch_for_shader(dim_shader(), 'TRIS', {"pos": co.reshape(n, 3)}, indices=tris.reshape(nt, 3))
    _dim["batches"][obj_eval.name] = (sig, me.name, batch)
    return batch


def draw_dim():
    """POST_VIEW вида 3D: другие видимые меш-объекты чуть темнее (только в Sculpt, с включённым чистым интерфейсом)."""
    ctx = bpy.context
    if ctx.mode != 'SCULPT' or _dim["failed"]:
        return
    p = prefs()
    alpha = getattr(p, "fade_others", _Defaults.fade_others)
    space = ctx.space_data
    if (alpha <= 0.0 or not (p.controls_on and p.focus_sculpt) or space is None or space.type != 'VIEW_3D'
            or not space.overlay.show_overlays or space.shading.type not in {'SOLID', 'MATERIAL'}
            or space.shading.show_xray or ctx.region_data is None):
        return
    active = ctx.active_object
    targets = [o for o in ctx.visible_objects if o.type == 'MESH' and o != active]
    if not targets:
        return
    import gpu
    saved = (gpu.state.blend_get(), gpu.state.depth_test_get(), gpu.state.depth_mask_get())
    try:
        depsgraph = ctx.view_layer.depsgraph
        shader = dim_shader()
        persp = ctx.region_data.perspective_matrix
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.depth_mask_set(False)
        shader.bind()
        shader.uniform_float("color", (0.0, 0.0, 0.0, alpha))
        shader.uniform_float("bias", DIM_DEPTH_BIAS)
        for o in targets:
            ev = o.evaluated_get(depsgraph)
            batch = dim_batch(ev)
            shader.uniform_float("mvp", persp @ ev.matrix_world)
            batch.draw(shader)
    except Exception as e:      # шейдер не собрался и т. п.: штатное затемнение вместо своего
        _dim["failed"] = True
        print("Sculpt Fund: dim others:", e)
        if not bpy.app.timers.is_registered(apply_sculpt_focus):
            bpy.app.timers.register(apply_sculpt_focus, first_interval=0.0)
    finally:
        gpu.state.blend_set(saved[0])
        gpu.state.depth_test_set(saved[1])
        gpu.state.depth_mask_set(saved[2])


@persistent
def _dim_updates(scene, depsgraph=None):
    """Изменилась геометрия объекта — его буфер затемнения строится заново (при следующем кадре)."""
    batches = _dim["batches"]
    if not batches or depsgraph is None:
        return
    for update in depsgraph.updates:
        if not update.is_updated_geometry:
            continue
        idd = update.id
        if isinstance(idd, bpy.types.Object):
            batches.pop(idd.name, None)
        elif isinstance(idd, bpy.types.Mesh):
            for name in [k for k, v in batches.items() if v[1] == idd.name]:
                batches.pop(name, None)


# --- обратимый интерфейс Sculpt ------------------------------------------------------------------------
# No polling timer and no mesh inspection here. Dependency notifications compare
# only window/mode/editor identities; changes schedule one deferred layout update.
_focus_views = {}
_focus_timelines = {}
_timeline_restored = {}
_focus_last = None
_focus_applied = None       # подпись, с которой фокус применён сейчас (None — не применён / снят)
_focus_owner = object()
_timeline_header_draw = None
_timeline_header_wrapper = None


def focus_signature():
    enabled = prefs().controls_on and prefs().focus_sculpt
    return (enabled, tuple(
        (w.as_pointer(), w.screen.as_pointer(),
         w.view_layer.objects.active.mode if w.view_layer.objects.active else 'OBJECT',
         tuple((a.as_pointer(), a.type) for a in w.screen.areas))
        for w in bpy.context.window_manager.windows))


@persistent
def queue_focus_update(*_args):
    global _focus_last
    try:
        # Сетка Polyframe переезжает за активным объектом (Alt+клик, смена режима): ID-данные — только из таймера
        if polyframe_signature() != _poly_last and not bpy.app.timers.is_registered(sync_polyframe):
            bpy.app.timers.register(sync_polyframe, first_interval=0.0)
        signature = focus_signature()
        if signature == _focus_last:
            return
        _focus_last = signature
        if not bpy.app.timers.is_registered(apply_sculpt_focus):
            bpy.app.timers.register(apply_sculpt_focus, first_interval=0.0)
    except (ReferenceError, RuntimeError):
        pass


def subscribe_focus():
    """Native mode notifications also fire when no mesh/depsgraph work is needed."""
    bpy.msgbus.clear_by_owner(_focus_owner)
    for key in ((bpy.types.Window, "workspace"), (bpy.types.Object, "mode"),
                (bpy.types.LayerObjects, "active")):
        bpy.msgbus.subscribe_rna(key=key, owner=_focus_owner, args=(), notify=queue_focus_update)


_timeline_resets = [0]      # сколько раз понадобился сброс активного региона (для тестов)
_focus_errors = []          # последние ошибки свёртки таймлайна (фокус их не показывает) — для диагностики


def reset_active_region(window, screen):
    """screen.area_move отказывает (poll ED_operator_screen_mainwinactive), пока над окном «активен» регион, —
    то есть почти всегда, когда курсор над окном Blender: так таймлайн вживую не сворачивался (21.10.2026, в файле
    пользователя, сохранённом в Sculpt, он остался 35 px). Активный регион обнуляет смена экрана (ED_screen_exit),
    поэтому вид разворачивается на весь экран и сразу возвращается — в одном вызове, без перерисовки между ними,
    как переключение вкладок рабочих пространств. True — вернулись на тот же экран."""
    if screen.is_temporary or screen.show_fullscreen:
        return False
    area = next((a for a in screen.areas if a.type == 'VIEW_3D'), None) or screen.areas[0]
    with bpy.context.temp_override(window=window, screen=screen, area=area):
        bpy.ops.screen.screen_full_area()
    _timeline_resets[0] += 1
    for _attempt in range(2):          # ни в коем случае не оставить пользователя в развёрнутом виде
        temp = window.screen
        if temp == screen:
            break
        try:
            with bpy.context.temp_override(window=window, screen=temp, area=temp.areas[0]):
                bpy.ops.screen.back_to_previous()
        except RuntimeError as e:
            print("Sculpt Fund: back from maximized view:", e)
            with bpy.context.temp_override(window=window, screen=temp, area=temp.areas[0]):
                bpy.ops.screen.screen_full_area()
    return window.screen == screen


def resize_timeline(window, screen, area, height, reset=False, current=None):
    """Move its upper boundary; keep the actual Timeline editor and its data. reset — если граница не двигается из-за
    курсора над окном, сбросить активный регион (только из таймера фокуса: не при загрузке файла и выключении).
    current — настоящая высота, если area.height ещё не обновилась (её обновляет только следующая раскладка)."""
    cur = area.height if current is None else current
    if bpy.app.background or cur == height:
        return

    def move():
        with bpy.context.temp_override(window=window, screen=screen, area=area):
            bpy.ops.screen.area_move(
                x=area.x + area.width // 2, y=area.y + cur + 1,
                delta=int(height - cur), snap=False)
    try:
        move()
    except RuntimeError:
        if not reset or window.screen != screen or not reset_active_region(window, screen):
            raise
        move()


FOCUS_HIDDEN = ("show_floor", "show_ortho_grid", "show_axis_x", "show_axis_y")


def show_focus_overlays(space):
    """Пол, сетка и оси X/Y вне Sculpt всегда включены. Не «как было до входа»: файл, сохранённый в Sculpt, хранит их
    скрытыми, и после его открытия «как было» означало бы «скрыто» навсегда (так и было у пользователя 20.10)."""
    for prop in FOCUS_HIDDEN:
        setattr(space.overlay, prop, True)


FOCUS_BASELINE = ("show_overlays", "show_sculpt_mask", "show_fade_inactive", "fade_inactive_alpha")


def apply_focus_overlay(space):
    """Вид Sculpt: без пола, сетки и осей; Overlays и маска включены; другие объекты слегка затемнены — своим
    нейтральным слоем (draw_dim), штатное Fade Inactive Geometry выключено (оно красит их в цвет фона темы)."""
    ov = space.overlay
    for prop in FOCUS_HIDDEN:
        setattr(ov, prop, False)
    # Общий выключатель Gizmos (кнопка в шапке, Ctrl+Ё) прячет и гизмо W, и плитку кисти: в проекте пользователя он
    # оказался выключен — «гизмо не появляется, кисть пропала» (22.10.2026). В Sculpt он включён, вне — как было
    space.show_gizmo = True
    # The master switch must stay on: disabling it also hides masks.
    ov.show_overlays = True
    ov.show_sculpt_mask = True
    fade = getattr(prefs(), "fade_others", _Defaults.fade_others)
    ov.show_fade_inactive = fade > 0.0 and _dim["failed"]
    if fade > 0.0 and _dim["failed"]:
        ov.fade_inactive_alpha = fade


def restore_focus(allow_reset=False):
    global _focus_applied
    _focus_applied = None
    for key, entry in list(_focus_views.items()):
        win, screen, area, space, values = entry
        # Overlays first: a shelf failure must never leave the grid/axes hidden.
        try:
            show_focus_overlays(space)
            for prop, value in values["overlay"].items():
                setattr(space.overlay, prop, value)
            space.show_gizmo = values.get("gizmo", True)
        except (ReferenceError, RuntimeError, AttributeError):
            pass
        try:
            if values["shelf"] and not space.show_region_asset_shelf:
                with bpy.context.temp_override(window=win, screen=screen, area=area):
                    try:
                        space.show_region_asset_shelf = True
                    except AttributeError:
                        # In Object Mode the shelf has no active asset-shelf type
                        # and its RNA visibility property becomes read-only.
                        # Restore the region's hidden flag via Blender's operator.
                        bpy.ops.screen.region_toggle(region_type='ASSET_SHELF')
        except (ReferenceError, RuntimeError, AttributeError):
            pass
        _focus_views.pop(key, None)
    for key, entry in list(_focus_timelines.items()):
        try:
            win, screen, area, original, collapsed = entry
            # Respect manual resizing while focused.
            if abs(area.height - collapsed) <= 2:
                resize_timeline(win, screen, area, original, reset=allow_reset)
                # area.height обновится только при следующей раскладке: если сразу снова свернуть (restore → apply в
                # одном вызове), прежняя высота берётся отсюда, а не из ещё свёрнутой area.height
                _timeline_restored[key] = original
            area.tag_redraw()
        except (ReferenceError, RuntimeError, TypeError):
            pass
        _focus_timelines.pop(key, None)


_shelf_retry = {"left": 0}


def has_shelf_region(area):
    return any(r.type == 'ASSET_SHELF' for r in area.regions)


def hide_focus_shelves():
    """Shelf hiding needs Blender's region refresh after the mode switch: until then the RNA flag is read-only
    (asset shelf poll still failed from Object Mode). Retried a few times, only right after entering Sculpt."""
    waiting = False
    for win, screen, area, space, values in list(_focus_views.values()):
        try:
            if not has_shelf_region(area) or space.is_property_readonly("show_region_asset_shelf"):
                # Not refreshed for Sculpt yet. On the first Sculpt entry Blender also shows the shelf itself
                # at that refresh, so wait for it even when the flag still reads "hidden".
                waiting = True
            elif space.show_region_asset_shelf:
                space.show_region_asset_shelf = False
                area.tag_redraw()
        except (ReferenceError, RuntimeError, AttributeError):
            pass
    _shelf_retry["left"] -= 1
    return 0.05 if waiting and _shelf_retry["left"] > 0 else None


def apply_sculpt_focus():
    global _focus_last
    if _pivot.get("follow_shutdown", False):
        return None         # таймер пережил выключение аддона
    try:
        _apply_sculpt_focus()
    except Exception as error:
        # Do not remember a signature that was never applied: the next notification or redraw retries.
        _focus_last = None
        print("Sculpt Fund: sculpt focus:", error)
    try:
        set_rotate_snap_shift(sculpt_snap_wanted())
    except (RuntimeError, ReferenceError, AttributeError, TypeError) as error:
        print("Sculpt Fund: rotate snap keys:", error)
    return None


# Вращение СКМ с 1.4.8 штатное, а штатное щёлкает к осям по Alt (раскладка «View3D Rotate Modal»); в ZBrush это
# Shift, а Alt — сдвиг: «и Shift, и Alt привязывают к осям» (22.10.2026). Пока какое-то окно в Sculpt и управление
# ZBrush включено, Alt-строки этой раскладки выключены, а Shift-строки добавлены; вне Sculpt, при выключении ZB и
# аддона — как в Blender. Shift-строки те же, что убирает очистка ROTATE_MODAL_ITEMS (user_keymap_apply).
ROTATE_SNAP_ALT = ('LEFT_ALT', 'RIGHT_ALT')
ROTATE_SNAP_SHIFT = (("AXIS_SNAP_ENABLE", 'LEFT_SHIFT', 'PRESS'), ("AXIS_SNAP_DISABLE", 'LEFT_SHIFT', 'RELEASE'),
                     ("AXIS_SNAP_ENABLE", 'RIGHT_SHIFT', 'PRESS'), ("AXIS_SNAP_DISABLE", 'RIGHT_SHIFT', 'RELEASE'))


def sculpt_snap_wanted():
    if _pivot.get("follow_shutdown", False) or not prefs().controls_on:
        return False
    for win in bpy.context.window_manager.windows:
        obj = win.view_layer.objects.active
        if obj is not None and obj.mode == 'SCULPT':
            return True
    return False


def set_rotate_snap_shift(on):
    kc = bpy.context.window_manager.keyconfigs.user
    km = kc.keymaps.get("View3D Rotate Modal") if kc is not None else None
    if km is None:
        return
    for k in km.keymap_items:
        if (k.propvalue in ('AXIS_SNAP_ENABLE', 'AXIS_SNAP_DISABLE') and k.type in ROTATE_SNAP_ALT
                and not k.is_user_defined and k.active == on):
            k.active = not on
    ours = [k for k in km.keymap_items if k.is_user_defined and k.any and k.key_modifier == 'NONE'
            and (k.propvalue, k.type, k.value) in ROTATE_SNAP_SHIFT]
    if on:
        have = {(k.propvalue, k.type, k.value) for k in ours}
        for prop, type_, value in ROTATE_SNAP_SHIFT:
            if (prop, type_, value) not in have:
                km.keymap_items.new_modal(prop, type_, value, any=True)
    else:
        for k in ours:
            km.keymap_items.remove(k)


def _apply_sculpt_focus():
    global _focus_last, _focus_applied
    # Шаги аддона (ремеш, копия, отделение) проходят через Object Mode и обратно в одном таймере: уведомление о смене
    # режима приходит, когда всё уже снова как было. Тогда ничего не трогать — раньше таймлайн разворачивался и
    # сворачивался заново (Ctrl+R «показывает таймлайн», 22.10.2026)
    signature = focus_signature()
    if signature == _focus_applied:
        _focus_last = signature
        return None
    # Restore all previous states before collecting the current visible screens.
    # temp_override(screen=...) lets the old workspace be restored too.
    restore_focus(allow_reset=True)
    if prefs().controls_on and prefs().focus_sculpt:
        for win in bpy.context.window_manager.windows:
            obj = win.view_layer.objects.active
            if obj is None or obj.mode != 'SCULPT':
                continue
            screen = win.screen
            for area in screen.areas:
                if area.type != 'VIEW_3D':
                    continue
                space = area.spaces.active
                _focus_views[area.as_pointer()] = (win, screen, area, space, {
                    # no shelf region yet = first Sculpt entry; Blender would show the shelf
                    "shelf": space.show_region_asset_shelf if has_shelf_region(area) else True,
                    # пол / сетку / оси restore включает всегда (FOCUS_HIDDEN), здесь — как было: выключатель, маска,
                    # затемнение других объектов
                    "overlay": {p: getattr(space.overlay, p) for p in FOCUS_BASELINE},
                    "gizmo": space.show_gizmo})
                apply_focus_overlay(space)
                area.tag_redraw()
        if _focus_views:
            _shelf_retry["left"] = 40
            if hide_focus_shelves() is not None and not bpy.app.timers.is_registered(hide_focus_shelves):
                bpy.app.timers.register(hide_focus_shelves, first_interval=0.05)
        for win in bpy.context.window_manager.windows:
            obj = win.view_layer.objects.active
            if obj is None or obj.mode != 'SCULPT':
                continue
            screen = win.screen
            # список заранее: сброс активного региона (reset_active_region) на время меняет экран окна
            for area in [a for a in screen.areas if a.type == 'DOPESHEET_EDITOR']:
                if area.ui_type != 'TIMELINE':
                    continue
                # Only a Timeline immediately below a viewport is collapsed.
                # Other layouts and animation editors are left in place.
                above = any(a.type == 'VIEW_3D' and abs(a.x - area.x) <= 2
                            and abs(a.width - area.width) <= 2
                            and abs(a.y - (area.y + area.height)) <= 4 for a in screen.areas)
                if not above:
                    continue
                header = next((r for r in area.regions if r.type == 'HEADER'), None)
                height = max(24, header.height if header else 26)
                current = _timeline_restored.get(area.as_pointer())      # только что возвращён этим же вызовом
                original = area.height if current is None else current
                if original <= height + 4:
                    original = height * 2       # уже свёрнут (файл сохранён в Sculpt): прежняя высота неизвестна
                try:
                    resize_timeline(win, screen, area, height, reset=True, current=current)
                    # area.height is updated on the next layout pass, not when
                    # area_move returns. Remember the requested height.
                    _focus_timelines[area.as_pointer()] = (win, screen, area, original, height)
                    area.tag_redraw()
                except (ReferenceError, RuntimeError) as error:
                    _focus_errors.append("timeline: %s" % str(error).strip().splitlines()[0][:200])
                    del _focus_errors[:-10]
    _timeline_restored.clear()
    _focus_last = _focus_applied = focus_signature()
    return None


class SCULPTFUND_OT_brush_popup(bpy.types.Operator):
    """Открыть кисти скульптинга (также B); полка не занимает место постоянно"""
    bl_idname = "sculpt_fund.brush_popup"
    bl_label = "Кисти (B)"

    def invoke(self, context, event):
        area = context.area if context.area.type == 'VIEW_3D' else next(
            (a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
        if area is None:
            return {'CANCELLED'}
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if region is None:
            return {'CANCELLED'}
        with context.temp_override(area=area, region=region):
            return safe(bpy.ops.wm.call_asset_shelf_popover, 'INVOKE_DEFAULT',
                        name="VIEW3D_AST_brush_sculpt", report=self.report)


def draw_focus_timeline(self, context, original):
    if context.area.as_pointer() in _focus_timelines:
        self.layout.operator(SCULPTFUND_OT_brush_popup.bl_idname, text="Кисти", icon='BRUSH_DATA')
    else:
        original(self, context)


def brush_tile_rect(context):
    """Pixel bounds, clear of the toolbar and bottom shelf/header."""
    scale = context.preferences.system.ui_scale
    left, bottom = 12 * scale, 12 * scale
    for region in context.area.regions:
        if region.type == 'TOOLS' and region.width > 1:
            left = max(left, region.x + region.width - context.region.x + 8 * scale)
        if region.type in {'HEADER', 'TOOL_HEADER', 'ASSET_SHELF', 'ASSET_SHELF_HEADER'}:
            if region.height > 1 and region.y < context.region.y + context.region.height / 2:
                bottom = max(bottom, region.y + region.height - context.region.y + 8 * scale)
    size = max(48 * scale, min(128 * scale, context.region.width - left - 12 * scale,
                              context.region.height - bottom - 60 * scale))
    return left, bottom, size, size + 28 * scale


# Зажатый модификатор сразу показывает временный инструмент (22.10.2026: «Shift — Smooth должна отражаться, что
# она уже выбрана, а не когда применяю пером»; то же для Ctrl — маска и Ctrl+Shift — обрезка): плитка кисти внизу
# слева. Нажатия и отпускания Shift / Ctrl / Alt над видом отмечает sculpt_fund.mod_hint (событие идёт дальше);
# в Windows состояние ещё сверяется с клавиатурой (отпускание могло прийти, пока работал мазок).
MOD_KEY_CHECK = True        # тесты с выдуманными событиями выключают
MOD_KEYS = {'LEFT_SHIFT': "shift", 'RIGHT_SHIFT': "shift", 'LEFT_CTRL': "ctrl", 'RIGHT_CTRL': "ctrl",
            'LEFT_ALT': "alt", 'RIGHT_ALT': "alt"}
_mod_keys = {"shift": False, "ctrl": False, "alt": False}


def held_modifiers():
    held = dict(_mod_keys)
    if MOD_KEY_CHECK and os.name == 'nt':
        try:
            import ctypes
            state = ctypes.windll.user32.GetAsyncKeyState
            for key, vk in (("shift", 0x10), ("ctrl", 0x11), ("alt", 0x12)):
                held[key] = held[key] and bool(state(vk) & 0x8000)
        except (AttributeError, OSError):
            pass
    return held


def modifier_hint(context):
    """(что, клавиши) временного инструмента кисти при зажатом модификаторе или None."""
    if not prefs().controls_on or not brush_tool_active(context):
        return None
    held = held_modifiers()
    if held["ctrl"] and held["shift"]:
        return (CS_NAMES[prefs().cs_tool], "Ctrl+Shift")
    if held["ctrl"] and held["alt"]:
        return ("Стереть маску", "Ctrl+Alt")
    if held["ctrl"]:
        return ("Mask", "Ctrl · с фона — " + CTRL_SHORT[prefs().ctrl_bg_tool])
    if held["shift"] and not held["alt"]:
        return ("Smooth", "Shift")
    return None


def hint_brush_for(name):
    """Кисть скульпта с таким именем, уже загруженная в файл (Smooth для Shift, Mask для Ctrl), или None."""
    if name not in ("Smooth", "Mask"):
        return None
    return next((b for b in bpy.data.brushes if b.name == name and b.use_paint_sculpt), None)


class SCULPTFUND_OT_mod_hint(bpy.types.Operator):
    """Shift / Ctrl / Alt нажат или отпущен над видом: обновить плитку кисти (событие идёт дальше)"""
    bl_idname = "sculpt_fund.mod_hint"
    bl_label = "Modifier Hint"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        key = MOD_KEYS.get(event.type)
        for name in ("shift", "ctrl", "alt"):
            _mod_keys[name] = (event.value == 'PRESS') if name == key else bool(getattr(event, name, False))
        if context.area is not None:
            context.area.tag_redraw()
        return {'PASS_THROUGH'}


class SCULPTFUND_GT_brush_tile(bpy.types.Gizmo):
    """Current brush preview with native gizmo hit testing and popup action."""
    bl_idname = "SCULPTFUND_GT_brush_tile"

    def setup(self):
        self.use_draw_scale = False
        self.use_select_background = False
        self.use_tooltip = True
        self._textures = {}         # превью кистей: текущая и временные (Smooth / Mask) — без перечитывания при Shift

    def preview_texture(self, brush):
        import gpu
        preview = brush.preview if brush else None
        size = tuple(preview.image_size) if preview else (0, 0)
        key = (brush.as_pointer(), preview.as_pointer(), size) if preview else None
        if key is None:
            return None
        if key not in self._textures:
            if len(self._textures) > 4:
                self._textures.clear()
            self._textures[key] = None
            if size[0] and size[1]:
                # Never hand an RNA array to the GPU constructor: its sequence
                # conversion reads each element separately and can stall the UI
                # for seconds. Fetch the whole preview once into a flat buffer.
                from array import array
                count = size[0] * size[1] * 4
                pixels = array('f', [0.0]) * count
                preview.image_pixels_float.foreach_get(pixels)
                data = gpu.types.Buffer('FLOAT', count, pixels)
                self._textures[key] = gpu.types.GPUTexture(size, format='RGBA16F', data=data)
        return self._textures[key]

    def draw(self, context):
        import blf
        import gpu
        from gpu_extras.batch import batch_for_shader
        x, y, width, height = brush_tile_rect(context)
        scale = context.preferences.system.ui_scale
        brush = context.tool_settings.sculpt.brush
        hint = modifier_hint(context)       # зажат Shift / Ctrl / Ctrl+Shift: временный инструмент, как в ZBrush
        # Smooth / Mask — превью этой кисти, как будто она уже выбрана; инструмент без кисти (Trim и т. п.) — надписью
        hint_brush = hint_brush_for(hint[0]) if hint else None
        texture = self.preview_texture(hint_brush if hint else brush) if (hint_brush or not hint) else None
        theme = context.preferences.themes[0].user_interface
        border = tuple(theme.wcol_tool.inner_sel[:3]) if self.is_highlight or hint else (0.36, 0.36, 0.36)
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        def rectangle(px, py, w, h, color):
            shader.bind()
            shader.uniform_float("color", color)
            batch_for_shader(shader, 'TRI_FAN', {"pos": (
                (px, py), (px + w, py), (px + w, py + h), (px, py + h))}).draw(shader)

        blend = gpu.state.blend_get()
        try:
            gpu.state.blend_set('ALPHA')
            with gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
                gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(Matrix((
                    (2 / context.region.width, 0, 0, -1),
                    (0, 2 / context.region.height, 0, -1),
                    (0, 0, 1, 0), (0, 0, 0, 1))))
                rectangle(x, y, width, height, (*border, 1.0))
                rectangle(x + scale, y + scale, width - 2 * scale, height - 2 * scale,
                          (0.075, 0.075, 0.075, 1.0))
                if texture:
                    image_shader = gpu.shader.from_builtin('IMAGE')
                    image_shader.bind()
                    image_shader.uniform_sampler("image", texture)
                    pad = 4 * scale
                    ix, iy, extent = x + pad, y + 28 * scale, width - 2 * pad
                    batch_for_shader(image_shader, 'TRI_FAN', {
                        "pos": ((ix, iy), (ix + extent, iy), (ix + extent, iy + extent), (ix, iy + extent)),
                        "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
                    }).draw(image_shader)
                if hint and not texture:
                    blf.size(0, 17 * scale)
                    blf.color(0, 1.0, 1.0, 1.0, 1.0)
                    words, lines = hint[0].split(), []
                    for word in words:      # перенос по словам в ширину плитки
                        if lines and blf.dimensions(0, lines[-1] + " " + word)[0] <= width - 12 * scale:
                            lines[-1] += " " + word
                        else:
                            lines.append(word)
                    top = y + height / 2 + 10 * scale + (len(lines) - 1) * 11 * scale
                    for i, line in enumerate(lines):
                        blf.position(0, x + (width - blf.dimensions(0, line)[0]) / 2, top - i * 22 * scale, 0)
                        blf.draw(0, line)
                blf.size(0, 12 * scale)
                blf.color(0, 0.95, 0.95, 0.95, 1.0)
                if hint:
                    label = hint[0] + " · " + hint[1].split(" ·")[0] if texture else hint[1]
                else:
                    label = brush.name if brush else "Выбрать кисть"
                while len(label) > 1 and blf.dimensions(0, label)[0] > width - 16 * scale:
                    label = label[:-2] + "…"
                blf.position(0, x + (width - blf.dimensions(0, label)[0]) / 2, y + 9 * scale, 0)
                blf.draw(0, label)
                if not texture and not hint:
                    blf.size(0, 11 * scale)
                    placeholder = "Кисти · B"
                    blf.position(0, x + (width - blf.dimensions(0, placeholder)[0]) / 2,
                                 y + height / 2, 0)
                    blf.draw(0, placeholder)
        finally:
            gpu.state.blend_set(blend)

    def test_select(self, context, location):
        x, y, width, height = brush_tile_rect(context)
        return 0 if x <= location[0] <= x + width and y <= location[1] <= y + height else -1


class SCULPTFUND_GGT_brush_launcher(bpy.types.GizmoGroup):
    """Large current-brush tile in every focused Sculpt viewport."""
    bl_idname = "SCULPTFUND_GGT_brush_launcher"
    bl_label = "Кисти"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SHOW_MODAL_ALL'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT' and prefs().controls_on and prefs().focus_sculpt

    def setup(self, context):
        self.button = self.gizmos.new(SCULPTFUND_GT_brush_tile.bl_idname)
        self.button.target_set_operator(SCULPTFUND_OT_brush_popup.bl_idname)


def register_focus():
    global _timeline_header_draw, _timeline_header_wrapper
    _timeline_header_draw = bpy.types.DOPESHEET_HT_header.draw
    original = _timeline_header_draw
    def wrapper(self, context):
        return draw_focus_timeline(self, context, original)
    _timeline_header_wrapper = wrapper
    bpy.types.DOPESHEET_HT_header.draw = wrapper
    if _dim["handle"] is None:
        _dim["handle"] = bpy.types.SpaceView3D.draw_handler_add(draw_dim, (), 'WINDOW', 'POST_VIEW')
    subscribe_focus()
    queue_focus_update()


def unregister_focus():
    global _timeline_header_draw, _timeline_header_wrapper, _focus_last
    bpy.msgbus.clear_by_owner(_focus_owner)
    for timer in (apply_sculpt_focus, hide_focus_shelves, sync_polyframe):
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)
    if _dim["handle"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_dim["handle"], 'WINDOW')
        except (ValueError, RuntimeError):
            pass
        _dim["handle"] = None
    _dim["batches"].clear()
    _dim["shader"] = None
    restore_focus()
    try:
        set_polyframe_wires(False)
    except (ReferenceError, RuntimeError, AttributeError):
        pass
    _poly_wire.clear()
    if _timeline_header_draw is not None:
        remove_draw_wrapper(bpy.types.DOPESHEET_HT_header, _timeline_header_wrapper, _timeline_header_draw)
        _timeline_header_draw = None
        _timeline_header_wrapper = None
    _focus_last = None


# Route the two native Remesh panels through the checked command in Sculpt.
# Forward the original draw functions/layout so other Blender panel options and
# other modes remain unchanged; do not override the native C operator itself.
_remesh_panel_draws = {}
_remesh_panels_active = False


def remove_draw_wrapper(panel, wrapper, original):
    """Preserve callbacks appended by other addons after our registration."""
    current = panel.draw
    if current is wrapper:
        panel.draw = original
    else:
        functions = getattr(current, "_draw_funcs", None)
        if functions is not None:
            functions[:] = [original if fn is wrapper else fn for fn in functions]


class _RemeshLayout:
    def __init__(self, layout):
        object.__setattr__(self, "_layout", layout)

    def __setattr__(self, name, value):
        setattr(self._layout, name, value)

    def __getattr__(self, name):
        value = getattr(self._layout, name)
        if not callable(value):
            return value
        def call(*args, **kwargs):
            if name == 'operator' and args and args[0] == "object.voxel_remesh":
                args = (SCULPTFUND_OT_voxel_remesh.bl_idname,) + args[1:]
            result = value(*args, **kwargs)
            return _RemeshLayout(result) if isinstance(result, bpy.types.UILayout) else result
        return call


class _RemeshPanel:
    def __init__(self, panel):
        self._panel = panel
        self.layout = _RemeshLayout(panel.layout)

    def __getattr__(self, name):
        return getattr(self._panel, name)


def remesh_panel_draw(original):
    """Обёртка draw ровно с двумя параметрами. Blender передаёт в draw столько аргументов, сколько параметров
    объявлено у функции (co_argcount): лишний параметр, даже со значением по умолчанию, получал пустой указатель,
    и открытие панели Remesh роняло Blender (1.4–1.4.5; t53)."""
    def draw(self, context):
        if _remesh_panels_active and prefs().controls_on and context.mode == 'SCULPT':
            return original(_RemeshPanel(self), context)
        return original(self, context)
    return draw


def register_remesh_panels():
    global _remesh_panels_active
    _remesh_panels_active = True
    for name in ("VIEW3D_PT_sculpt_voxel_remesh", "DATA_PT_remesh"):
        panel = getattr(bpy.types, name, None)
        if panel is None:
            continue
        original = panel.draw
        draw = remesh_panel_draw(original)
        _remesh_panel_draws[name] = (original, draw)
        panel.draw = draw


def unregister_remesh_panels():
    global _remesh_panels_active
    _remesh_panels_active = False
    for name, (original, wrapper) in _remesh_panel_draws.items():
        panel = getattr(bpy.types, name, None)
        if panel is not None:
            remove_draw_wrapper(panel, wrapper, original)
    _remesh_panel_draws.clear()


# DynaMesh Resolution, как в ZBrush: вокселей по наибольшей стороне объекта. Хранится как обычный Voxel Size меша
# (его же берут Ctrl+R, пустая Ctrl-рамка и штатный Remesh), ползунок только пересчитывает: размер / разрешение.
def local_max_extent(obj):
    bb = [Vector(c) for c in obj.bound_box]
    return max(max(c[i] for c in bb) - min(c[i] for c in bb) for i in range(3))


def _dyna_res_get(obj):
    try:
        size, voxel = local_max_extent(obj), obj.data.remesh_voxel_size
    except (AttributeError, ValueError):
        return 128
    if size <= 0.0 or voxel <= 0.0:
        return 128
    return max(4, min(8192, int(round(size / voxel))))


def _dyna_res_set(obj, value):
    try:
        size = local_max_extent(obj)
        if size > 0.0:
            obj.data.remesh_voxel_size = size / max(int(value), 1)
    except (AttributeError, ValueError) as e:
        print("Sculpt Fund: DynaMesh resolution:", e)


class SCULPTFUND_OT_backface_mask(bpy.types.Operator):
    """BackfaceMask, как в ZBrush: активная кисть не задевает обратную сторону тонких мест (губы, веки, уши) —
    штатное Front Faces Only этой кисти"""
    bl_idname = "sculpt_fund.backface_mask"
    bl_label = "BackfaceMask"

    @classmethod
    def poll(cls, context):
        sculpt = context.tool_settings.sculpt
        return context.mode == 'SCULPT' and sculpt is not None and sculpt.brush is not None

    def execute(self, context):
        brush = context.tool_settings.sculpt.brush
        try:
            brush.use_frontface = not brush.use_frontface
        except (AttributeError, TypeError, RuntimeError) as e:
            self.report({'WARNING'}, "BackfaceMask: кисть «%s» не меняется (%s)" % (brush.name, e))
            return {'CANCELLED'}
        self.report({'INFO'}, "BackfaceMask «%s»: %s" % (brush.name, "вкл" if brush.use_frontface else "выкл"))
        return {'FINISHED'}


def draw_header(self, context):
    """Компактно, в начале шапки инструментов: вкл/выкл, Ctrl+Shift-инструмент, DynaMesh, Customize."""
    # A mode change always redraws the header, even when a third-party operator
    # skips normal RNA/depsgraph notifications. Schedule, never edit UI in draw.
    queue_focus_update()
    if context.mode != 'SCULPT':
        return
    layout = self.layout
    on = prefs().controls_on
    row = layout.row(align=True)
    row.operator(SCULPTFUND_OT_toggle.bl_idname, text="ZB", icon='CHECKBOX_HLT' if on else 'CHECKBOX_DEHLT', depress=on)
    if on:
        row.operator(SCULPTFUND_OT_brush_popup.bl_idname, text="", icon='BRUSH_DATA')
        row.menu(SCULPTFUND_MT_ctrl_menu.bl_idname, text="Ctrl: " + CTRL_SHORT[prefs().ctrl_bg_tool])
        row.menu(SCULPTFUND_MT_cs_menu.bl_idname, text=CS_NAMES[prefs().cs_tool])
        obj = context.active_object
        if obj is not None and obj.type == 'MESH':
            sub = row.row(align=True)
            sub.ui_units_x = 5
            sub.prop(obj, "sculpt_fund_dyna_res", text="Res", slider=True)
        row.menu(SCULPTFUND_MT_primitive_menu.bl_idname, text="", icon='MESH_UVSPHERE')
    layout.separator()


class SCULPTFUND_PT_panel(bpy.types.Panel):
    """Вкладка ZBrush в боковой панели (N) в Sculpt Mode"""
    bl_label = "ZBrush Controls"
    bl_idname = "SCULPTFUND_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZBrush"

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT'

    def draw(self, context):
        p = prefs()
        col = self.layout.column()
        on = p.controls_on
        col.operator(SCULPTFUND_OT_toggle.bl_idname, text="Управление ZBrush: " + ("вкл" if on else "выкл"),
                     icon='CHECKBOX_HLT' if on else 'CHECKBOX_DEHLT', depress=on)
        col.label(text="Быстро: Ctrl+Shift+Alt+Z или кнопка ZB в шапке")
        if not on:
            return
        col.separator()
        col.label(text="Ctrl с пустого места (Ctrl+B):")
        col.menu(SCULPTFUND_MT_ctrl_menu.bl_idname, text=CTRL_NAMES[p.ctrl_bg_tool])
        col.label(text="Ctrl+Shift-инструмент:")
        col.menu(SCULPTFUND_MT_cs_menu.bl_idname, text=CS_NAMES[p.cs_tool])
        obj = context.active_object
        if obj is not None and obj.type == 'MESH':
            col.separator()
            row = col.row(align=True)
            row.label(text="DynaMesh (Ctrl+R):", icon='MOD_REMESH')
            row.prop(obj, "sculpt_fund_dyna_res", text="Resolution", slider=True)
            row = col.row(align=True)
            row.prop(obj.data, "remesh_voxel_size", text="Voxel Size")
            row.operator(SCULPTFUND_OT_voxel_remesh.bl_idname, text="Remesh", icon='MOD_REMESH')
            brush = context.tool_settings.sculpt.brush
            if brush is not None:
                col.prop(brush, "use_frontface", text="BackfaceMask: " + brush.name)
            row = col.row(align=True)
            row.operator(SCULPTFUND_OT_split_masked.bl_idname, icon='MOD_MASK')
            col.operator(SCULPTFUND_OT_delete_hidden.bl_idname, icon='TRASH')
        col.separator()
        col.menu(SCULPTFUND_MT_primitive_menu.bl_idname, text="Заменить примитивом", icon='MESH_UVSPHERE')
        if isinstance(p, bpy.types.AddonPreferences):
            col.prop(p, "split_in_quick")
        col.separator()
        col.label(text="Гизмо (W — стрелки, E — полное):")
        row = col.row(align=True)
        row.operator(SCULPTFUND_OT_pivot_unmasked.bl_idname, text="Центр", icon='PIVOT_MEDIAN')
        row.operator(SCULPTFUND_OT_gizmo_world.bl_idname, text="Оси по миру", icon='ORIENTATION_GLOBAL')
        col.label(text="Полигруппы (Alt+W):")
        grid = col.grid_flow(columns=2, align=True)
        grid.operator("sculpt.face_sets_init", text="Auto Groups").mode = 'LOOSE_PARTS'
        grid.operator("sculpt.face_sets_create", text="Group Visible").mode = 'VISIBLE'
        grid.operator("sculpt.face_sets_init", text="By Normals").mode = 'NORMALS'
        grid.operator("sculpt.face_sets_create", text="Group Masked").mode = 'MASKED'
        if isinstance(p, bpy.types.AddonPreferences):
            col.prop(p, "polyframe_wire")
            col.prop(p, "fade_others", slider=True)
        if isinstance(p, bpy.types.AddonPreferences):
            col.separator()
            col.label(text="Навигация (кроме кнопки пера / СКМ):")
            col.prop(p, "nav_mode", text="")
            col.prop(p, "use_canvas_masking")


# --- настройки аддона -----------------------------------------------------------------------------------

NAV_MODES = (
    ('PEN', "Только кнопка пера / СКМ", "ЛКМ по фону ничего не вращает (Grab цепляет меш и с фона)", 0),
    ('LMB', "ЛКМ по фону", "Как в ZBrush: протяжка по пустому месту — вращение, Alt — сдвиг, Shift — щелчок к осям", 1),
    ('RMB', "ПКМ где угодно", "ПКМ — вращение и над мешем, Alt+ПКМ — сдвиг, Ctrl+ПКМ — зум (вместо контекстного меню)", 2),
    ('BOTH', "ЛКМ по фону и ПКМ", "Обе навигации", 3),
)


def _nav_get(self):
    return (0 if self.disable_lmb_navigation else 1) + (2 if self.use_rmb_nav else 0)


def _nav_set(self, value):
    lmb, rmb = bool(value & 1), bool(value & 2)
    if self.disable_lmb_navigation != (not lmb):
        self.disable_lmb_navigation = not lmb       # update пересобирает раскладку
    if self.use_rmb_nav != rmb:
        self.use_rmb_nav = rmb


def update_keymaps(self, context):
    unregister_keymaps()
    register_keymaps()
    try:
        context.window_manager.keyconfigs.update()   # иначе итоговая раскладка не пересобирается до перезапуска
    except Exception as e:
        print("Sculpt Fund: keyconfig update:", e)


def update_controls(self, context):
    update_keymaps(self, context)
    try:
        user_keymap_apply(self.controls_on)
    except Exception as e:
        print("Sculpt Fund: keymap:", e)
    queue_focus_update()
    for win in context.window_manager.windows:
        for area in win.screen.areas:
            area.tag_redraw()


def update_fade(self, context):
    """Ползунок затемнения: только оверлей открытых Sculpt-видов (без перестройки интерфейса и таймлайна)."""
    for _win, _screen, area, space, _values in list(_focus_views.values()):
        try:
            apply_focus_overlay(space)
            area.tag_redraw()
        except (ReferenceError, RuntimeError, AttributeError):
            pass


class SCULPTFUND_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    controls_on: BoolProperty(name="Управление ZBrush включено", default=True, update=update_controls,
                              description="Выключить — обычный Blender без удаления аддона (кнопка ZBrush в шапке, Ctrl+Shift+Alt+Z)")
    cs_tool: EnumProperty(name="Ctrl+Shift", default='TRIM_LASSO', items=[(t[0], t[1], t[2]) for t in CS_TOOLS])
    # новое имя: в 1.2 было ctrl_tool с кистью по умолчанию; по мешу теперь всегда кисть, здесь — фигура с пустого места
    ctrl_bg_tool: EnumProperty(name="Ctrl с пустого места", default='MASK_BOX', items=[(t[0], t[1], t[2]) for t in CTRL_TOOLS])
    disable_lmb_navigation: BoolProperty(name="Отключить навигацию на ЛКМ", default=True, update=update_keymaps,
                                         description="Не вращать и не перемещать вид левой кнопкой. "
                                                     "СКМ/кнопка пера, кисти, маски и Alt-клик сохраняются. "
                                                     "Снять галочку — классическая навигация по фону")
    use_canvas_masking: BoolProperty(name="Ctrl по пустому месту", default=True,
                                     description="Ctrl+клик по фону = инверсия маски; пустая рамка = сброс маски, без маски — DynaMesh")
    split_in_quick: BoolProperty(name="«Отделить замаскированное» в Quick Favorites (Tab)", default=True)
    focus_sculpt: BoolProperty(name="Чистый интерфейс Sculpt", default=True, update=update_controls,
                              description="Скрыть постоянную полку кистей, сетку и оси X/Y; свернуть таймлайн "
                                          "в кнопку кистей. Вне Sculpt восстановить прежний вид")
    use_rmb_nav: BoolProperty(name="Навигация правой кнопкой (и над мешем)", default=False, update=update_keymaps,
                              description="ПКМ = вращение, Alt+ПКМ = сдвиг, Ctrl+ПКМ = зум. В Blender на ПКМ контекстное меню")
    # Одна настройка вместо двух галочек («почему навигация включается в две кнопки», 22.10.2026); хранится в них же
    nav_mode: EnumProperty(name="Навигация", get=_nav_get, set=_nav_set, items=NAV_MODES,
                           description="Чем, кроме кнопки пера / СКМ, вращать вид")
    fade_others: FloatProperty(name="Затемнять другие объекты", default=0.25, min=0.0, max=0.9, subtype='FACTOR',
                               update=update_fade,
                               description="В Sculpt объект, который скульптишь, виден как обычно, остальные — чуть "
                                           "темнее (нейтрально, без цвета фона темы). 0 — не затемнять")
    polyframe_wire: BoolProperty(name="Shift+F: и сетка", default=False, update=update_polyframe,
                                 description="Polyframe (Shift+F) показывает цвета полигрупп; с галочкой — ещё и сетку, "
                                             "только у активного объекта")

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "controls_on")
        col.separator()
        col.prop(self, "nav_mode")
        col.prop(self, "use_canvas_masking")
        col.prop(self, "ctrl_bg_tool")
        col.prop(self, "cs_tool")
        col.prop(self, "split_in_quick")
        col.prop(self, "focus_sculpt")
        col.prop(self, "fade_others")
        col.prop(self, "polyframe_wire")
        col.label(text="Кисти с Size Pressure: " + brush_dir())


# --- раскладка ------------------------------------------------------------------------------------------

_pending = []


def kmi(km, idname, type_, value, props=None, **mods):
    _pending.append((km, idname, type_, value, props, mods))


def flush_keymaps():
    # Blender ставит строки addon-раскладки в итоговую раскладку в обратном порядке (последняя — первой),
    # поэтому добавляем с конца: в итоге порядок совпадает с порядком в register_keymaps().
    for km, idname, type_, value, props, mods in reversed(_pending):
        item = km.keymap_items.new(idname, type_, value, **mods)
        for k, v in (props or {}).items():
            setattr(item.properties, k, v)
        addon_keymaps.append((km, item))
    _pending.clear()


def register_keymaps():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return
    km = kc.keymaps.new("Sculpt", space_type='EMPTY', region_type='WINDOW')
    kmi(km, SCULPTFUND_OT_toggle.bl_idname, 'Z', 'PRESS', ctrl=True, alt=True, shift=True)
    if not prefs().controls_on:
        flush_keymaps()
        return
    # Порядок важен. Мазки кисти стоят первыми и с Ignore Background Click: если под пером меш — это обычный мазок
    # (проверяет сам Blender, без Python); если фон — событие уходит ниже, к жестам ZBrush.
    bg = {'ignore_background_click': True}
    brush_bg = {'ignore_background_click': not prefs().disable_lmb_navigation}
    # Другой объект — только быстрым двойным Alt+кликом (21.10.2026): одиночный Alt+клик — инверсия кисти / центр гизмо
    kmi(km, SCULPTFUND_OT_alt_select.bl_idname, 'LEFTMOUSE', 'DOUBLE_CLICK', alt=True)
    for key in MOD_KEYS:                        # подсказка временного инструмента на плитке кисти
        for value in ('PRESS', 'RELEASE'):
            kmi(km, SCULPTFUND_OT_mod_hint.bl_idname, key, value, any=True)
    kmi(km, SCULPTFUND_OT_zb_grab.bl_idname, 'LEFTMOUSE', 'PRESS')     # Grab — свой (Move ZBrush), иначе мимо
    if not prefs().disable_lmb_navigation:
        for mods in ({}, dict(shift=True), dict(alt=True)):
            kmi(km, SCULPTFUND_OT_canvas.bl_idname, 'LEFTMOUSE', 'PRESS', {'grab_check': True}, **mods)
    kmi(km, "sculpt.brush_stroke", 'LEFTMOUSE', 'PRESS', dict(brush_bg))
    kmi(km, "sculpt.brush_stroke", 'LEFTMOUSE', 'PRESS', dict(brush_bg, brush_toggle='SMOOTH'), shift=True)
    kmi(km, "sculpt.brush_stroke", 'LEFTMOUSE', 'PRESS', dict(bg, mode='INVERT'), alt=True)
    if prefs().disable_lmb_navigation:
        kmi(km, SCULPTFUND_OT_alt_click.bl_idname, 'LEFTMOUSE', 'CLICK', alt=True)
    else:
        for mods in ({}, dict(shift=True), dict(alt=True)):
            kmi(km, SCULPTFUND_OT_canvas.bl_idname, 'LEFTMOUSE', 'PRESS', **mods)
    if prefs().use_rmb_nav:
        for mods in ({}, dict(alt=True), dict(ctrl=True)):
            kmi(km, SCULPTFUND_OT_canvas.bl_idname, 'RIGHTMOUSE', 'PRESS', {'button': 'RIGHTMOUSE', 'anywhere': True}, **mods)
    # Ctrl / Ctrl+Alt, как в ZBrush: по мешу — мазок кисти маски (стоит первым, с Ignore Background Click; в режиме
    # гизмо мазок не запускается), с пустого места — своя рамка / лассо. Клик свободен для блюра и шарпа.
    # Mask Lasso — лассо и по мешу (строки до кисти маски; при Box / Line они пропускают событие дальше)
    kmi(km, SCULPTFUND_OT_gesture.bl_idname, 'LEFTMOUSE', 'CLICK_DRAG', {'target': 'MASK', 'on_mesh': True}, ctrl=True)
    kmi(km, SCULPTFUND_OT_gesture.bl_idname, 'LEFTMOUSE', 'CLICK_DRAG', {'target': 'MASK', 'on_mesh': True},
        ctrl=True, alt=True)
    kmi(km, "sculpt.brush_stroke", 'LEFTMOUSE', 'CLICK_DRAG', dict(bg, brush_toggle='MASK', mode='NORMAL'), ctrl=True)
    kmi(km, "sculpt.brush_stroke", 'LEFTMOUSE', 'CLICK_DRAG', dict(bg, brush_toggle='MASK', mode='INVERT'), ctrl=True, alt=True)
    kmi(km, SCULPTFUND_OT_gesture.bl_idname, 'LEFTMOUSE', 'CLICK_DRAG', {'target': 'MASK'}, ctrl=True)
    kmi(km, SCULPTFUND_OT_gesture.bl_idname, 'LEFTMOUSE', 'CLICK_DRAG', {'target': 'MASK'}, ctrl=True, alt=True)
    kmi(km, SCULPTFUND_OT_mask_click.bl_idname, 'LEFTMOUSE', 'CLICK', {'filter_type': 'SMOOTH'}, ctrl=True)
    kmi(km, SCULPTFUND_OT_mask_click.bl_idname, 'LEFTMOUSE', 'CLICK', {'filter_type': 'SHARPEN'}, ctrl=True, alt=True)
    # Ctrl+Shift
    kmi(km, SCULPTFUND_OT_cs_click.bl_idname, 'LEFTMOUSE', 'CLICK', ctrl=True, shift=True)
    kmi(km, "paint.visibility_invert", 'LEFTMOUSE', 'CLICK', ctrl=True, shift=True, alt=True)
    kmi(km, SCULPTFUND_OT_gesture.bl_idname, 'LEFTMOUSE', 'CLICK_DRAG', {'target': 'CS'}, ctrl=True, shift=True)
    kmi(km, SCULPTFUND_OT_gesture.bl_idname, 'LEFTMOUSE', 'CLICK_DRAG', {'target': 'CS'}, ctrl=True, shift=True, alt=True)
    kmi(km, "wm.call_menu_pie", 'MIDDLEMOUSE', 'PRESS', {'name': SCULPTFUND_MT_cs_pie.bl_idname}, ctrl=True, shift=True)
    kmi(km, "wm.call_menu_pie", 'B', 'PRESS', {'name': SCULPTFUND_MT_ctrl_pie.bl_idname}, ctrl=True)
    # Навигация кнопкой пера / колесом. СКМ — штатное вращение Blender (раскладка «3D View»): плавное, со всеми
    # настройками Navigation (вокруг последнего мазка, Auto Depth, Auto Perspective); своё вращение на Python на СКМ
    # подлагивало (21.10.2026). Alt+СКМ — штатный сдвиг, Shift+СКМ — своё вращение со щелчком к осям (ZBrush)
    kmi(km, "view3d.move", 'MIDDLEMOUSE', 'PRESS', alt=True)
    kmi(km, SCULPTFUND_OT_canvas.bl_idname, 'MIDDLEMOUSE', 'PRESS', {'button': 'MIDDLEMOUSE', 'anywhere': True},
        shift=True)
    # Клавиши ZBrush
    size = dict(RADIAL_COMMON, data_path_primary='tool_settings.sculpt.brush.size',
                data_path_secondary='tool_settings.sculpt.unified_paint_settings.size',
                use_secondary='tool_settings.sculpt.unified_paint_settings.use_unified_size')
    kmi(km, "wm.radial_control", 'SPACE', 'PRESS', dict(size, release_confirm=True))
    kmi(km, "wm.radial_control", 'U', 'PRESS', dict(RADIAL_COMMON, data_path_primary='tool_settings.sculpt.brush.strength',
        data_path_secondary='tool_settings.sculpt.unified_paint_settings.strength',
        use_secondary='tool_settings.sculpt.unified_paint_settings.use_unified_strength'))
    kmi(km, "wm.radial_control", 'O', 'PRESS', dict(RADIAL_COMMON, data_path_primary='tool_settings.sculpt.brush.hardness'))
    kmi(km, SCULPTFUND_OT_frame.bl_idname, 'F', 'PRESS')
    # Ctrl+R — штатная правка Voxel Size с квадратом сетки вокселей (то, что раньше было на R); ремеш — пустая Ctrl-рамка
    kmi(km, "object.voxel_size_edit", 'R', 'PRESS', ctrl=True)
    kmi(km, SCULPTFUND_OT_polyframe.bl_idname, 'F', 'PRESS', shift=True)
    kmi(km, "wm.context_toggle", 'L', 'PRESS', {'data_path': 'tool_settings.sculpt.brush.use_smooth_stroke'})
    kmi(km, SCULPTFUND_OT_symmetry.bl_idname, 'X', 'PRESS')     # симметрия вкл / выкл с прежними осями
    kmi(km, "wm.call_asset_shelf_popover", 'B', 'PRESS', {'name': 'VIEW3D_AST_brush_sculpt'})
    kmi(km, SCULPTFUND_OT_gizmo_tool.bl_idname, 'W', 'PRESS', {'tool': 'builtin.move'})
    kmi(km, SCULPTFUND_OT_gizmo_tool.bl_idname, 'E', 'PRESS', {'tool': 'builtin.transform'})
    kmi(km, SCULPTFUND_OT_xform_key.bl_idname, 'S', 'PRESS', {'kind': 'SCALE'})     # S — масштаб вокруг центра гизмо
    # G / R — штатные перенос и поворот, как в Object Mode (незамаскированное); X / Y / Z первым нажатием — оси гизмо
    # (ориентация сцены), вторым — другие оси Blender
    kmi(km, SCULPTFUND_OT_xform_key.bl_idname, 'G', 'PRESS', {'kind': 'TRANSLATE'})
    kmi(km, SCULPTFUND_OT_xform_key.bl_idname, 'R', 'PRESS', {'kind': 'ROTATE'})
    kmi(km, SCULPTFUND_OT_pivot_surface.bl_idname, 'RIGHTMOUSE', 'PRESS', shift=True)
    kmi(km, "wm.call_menu_pie", 'W', 'PRESS', {'name': SCULPTFUND_MT_polygroups_pie.bl_idname}, alt=True)
    kmi(km, "wm.tool_set_by_id", 'Q', 'PRESS', {'name': 'builtin.brush'})                 # Q — кисть, как Draw в ZBrush
    kmi(km, "wm.call_menu", 'TAB', 'PRESS', {'name': SCULPTFUND_MT_quick.bl_idname})     # Tab — Quick Favorites
    kmi(km, SCULPTFUND_OT_subdiv_level.bl_idname, 'D', 'PRESS', {'delta': 1})
    kmi(km, SCULPTFUND_OT_subdiv_level.bl_idname, 'D', 'PRESS', {'delta': -1}, shift=True)
    kmi(km, SCULPTFUND_OT_divide.bl_idname, 'D', 'PRESS', ctrl=True)
    kmi(km, "paint.mask_flood_fill", 'A', 'PRESS', {'mode': 'VALUE', 'value': 1.0}, ctrl=True)
    kmi(km, "wm.context_toggle", 'H', 'PRESS', {'data_path': 'space_data.overlay.show_sculpt_mask'}, ctrl=True)
    kmi(km, SCULPTFUND_OT_group_masked.bl_idname, 'W', 'PRESS', ctrl=True)
    kmi(km, "wm.call_menu_pie", 'A', 'PRESS', {'name': SCULPTFUND_MT_primitive_pie.bl_idname}, shift=True)
    for key, shift, name in BRUSH_KEYS:
        kmi(km, "brush.asset_activate", key, 'PRESS', {
            'asset_library_type': 'CUSTOM', 'asset_library_identifier': LIB_NAME,
            'relative_asset_identifier': "Saved/Brushes/%s/Brush/%s" % (brush_file(name), name)}, shift=shift)
    # Режим гизмо. Раскладки инструментов Move / Transform / Rotate / Scale стоят раньше раскладки Sculpt: их
    # «протяжка откуда угодно» забирала и фон. Наши строки — до неё: по фону навигация, Alt по мешу — центр по поверхности.
    for keymap_name in GIZMO_TOOLS.values():
        kmt = kc.keymaps.new(keymap_name, space_type='VIEW_3D', region_type='WINDOW')
        kmi(kmt, SCULPTFUND_OT_alt_select.bl_idname, 'LEFTMOUSE', 'DOUBLE_CLICK', {'from_tool': True}, alt=True)
        for mods in ({}, dict(shift=True), dict(alt=True)):
            kmi(kmt, SCULPTFUND_OT_canvas.bl_idname, 'LEFTMOUSE', 'PRESS', {'from_tool': True}, **mods)
        if prefs().disable_lmb_navigation:
            kmi(kmt, SCULPTFUND_OT_canvas.bl_idname, 'LEFTMOUSE', 'CLICK_DRAG', {'from_tool': True}, alt=True)
    # Ручки гизмо: нажатие — точный центр гизмо; Ctrl+протяжка стрелки / центра — копия незамаскированного;
    # Alt+протяжка — гизмо без меша (стрелка — по оси, центр — свободно, кольцо — поворот осей)
    kmg = kc.keymaps.new("Generic Gizmo Maybe Drag", space_type='EMPTY', region_type='WINDOW')
    kmi(kmg, SCULPTFUND_OT_gizmo_press.bl_idname, 'LEFTMOUSE', 'CLICK_DRAG', {'dup': True}, ctrl=True)
    kmi(kmg, SCULPTFUND_OT_gizmo_alt.bl_idname, 'LEFTMOUSE', 'CLICK_DRAG', alt=True)
    kmi(kmg, SCULPTFUND_OT_gizmo_scale.bl_idname, 'LEFTMOUSE', 'CLICK_DRAG')      # кубик при повёрнутых осях
    kmi(kmg, SCULPTFUND_OT_gizmo_press.bl_idname, 'LEFTMOUSE', 'PRESS', {'dup': False}, any=True)
    # Ctrl+Z / Ctrl+Shift+Z: в Sculpt — без выхода в Object Mode, вне Sculpt оператор пропускает их штатным
    kms = kc.keymaps.new("Screen", space_type='EMPTY', region_type='WINDOW')
    kmi(kms, SCULPTFUND_OT_history.bl_idname, 'Z', 'PRESS', {'redo': False}, ctrl=True, repeat=True)
    kmi(kms, SCULPTFUND_OT_history.bl_idname, 'Z', 'PRESS', {'redo': True}, ctrl=True, shift=True, repeat=True)
    flush_keymaps()


def unregister_keymaps():
    for km, item in addon_keymaps:
        try:
            km.keymap_items.remove(item)
        except (ReferenceError, RuntimeError):
            pass
    addon_keymaps.clear()


def mods_of(k):
    return (bool(k.ctrl), bool(k.shift), bool(k.alt))


def user_keymap_apply(enable):
    """Правки в user-раскладке, которые нельзя сделать addon-раскладкой. enable=False — откат."""
    kc = bpy.context.window_manager.keyconfigs.user
    km = kc.keymaps.get("Sculpt")
    if km is not None:
        for idname, type_, value, ctrl, shift, alt in DISABLED_DEFAULTS:
            for k in km.keymap_items:
                if k.idname == idname and k.type == type_ and k.value == value and mods_of(k) == (ctrl, shift, alt):
                    k.active = not enable
        # The native temporary MASK on Alt PRESS would swallow a background
        # press before our separate Alt CLICK. Do not disable our INVERT brush
        # or user-defined custom items with the same chord.
        for k in km.keymap_items:
            if (k.idname == "sculpt.brush_stroke" and k.type == 'LEFTMOUSE' and k.value == 'PRESS'
                    and mods_of(k) == (False, False, True) and not k.is_user_defined
                    and k.properties.brush_toggle == 'MASK'):
                k.active = not enable
            # Штатные Ctrl+0…5 (уровень подразделения) в Sculpt молча добавляют Multires. Здесь Ctrl — маска, а 1–4 —
            # кисти: Ctrl+1 под рукой и ставил Multires, которого пользователь не просил (20.10.2026)
            if (k.idname == "object.subdivision_set" and k.type in SUBDIV_SET_KEYS and k.value == 'PRESS'
                    and mods_of(k) == (True, False, False) and not k.is_user_defined
                    and getattr(k.properties, "ensure_modifier", True)):
                k.active = not enable
    rm = kc.keymaps.get("View3D Rotate Modal")
    if rm is not None:
        for prop, type_, value, mods in ROTATE_MODAL_ITEMS:
            found = [k for k in rm.keymap_items if k.propvalue == prop and k.type == type_ and k.value == value
                     and bool(k.any) == bool(mods.get('any')) and k.key_modifier == 'NONE'
                     and (k.any or (mods_of(k) == (False, bool(mods.get('shift')), False) and not k.oskey))]
            for k in found:
                if k.is_user_defined:
                    rm.keymap_items.remove(k)
    set_rotate_snap_shift(enable and sculpt_snap_wanted())      # в Sculpt — Shift вместо Alt (см. выше)


# --- кисти с Size Pressure ------------------------------------------------------------------------------

# Grab (клавиша 3) как Move в ZBrush: цепляет меш своим радиусом, даже если перо мимо меша или над другим объектом —
# штатное Falloff Shape: Projected (Blender при промахе луча берёт ближайшую к лучу точку меша в радиусе кисти,
# sculpt.cc, stroke_get_location_bvh_ex). Projected тянет и обратную сторону тонких мест, поэтому сразу BackfaceMask
# (Front Faces Only); переключатель — в Tab и панели N.
BRUSH_DEFAULTS = {"Grab": {"falloff_shape": 'SPHERE', "use_frontface": False}}
# 1.4.9: BackfaceMask у Grab по умолчанию выключен (22.10.2026). 1.5.1: Grab — свой оператор (zb_grab: с фона цепляет
# сам), штатному — обратно Sphere: Projected тянул всё за точкой нажатия («несколько грабов», 27.10.2026)
BRUSH_REV = 4


def apply_brush_defaults(brush, name, only=None):
    for prop, value in BRUSH_DEFAULTS.get(name, {}).items():
        if only is None or prop in only:
            setattr(brush, prop, value)
    brush["sculpt_fund_rev"] = BRUSH_REV


def upgrade_brush_assets(sub):
    """Кисти, созданные прежними версиями, получают новые умолчания (в отдельном временном bpy.data: файл сцены и
    уже подключённые кисти не затрагиваются; подключённая сейчас кисть обновится со следующего запуска)."""
    for name in BRUSH_DEFAULTS:
        path = os.path.join(sub, brush_file(name))
        if not os.path.exists(path):
            continue
        try:
            with bpy.data.temp_data() as temp:
                with temp.libraries.load(path, link=False) as (_src, dst):
                    dst.brushes = [name]
                brush = dst.brushes[0]
                rev = brush.get("sculpt_fund_rev", 1) if brush is not None else BRUSH_REV
                if rev >= BRUSH_REV:
                    continue
                # с rev 3 BackfaceMask уже выбирал пользователь: менять только Falloff
                apply_brush_defaults(brush, name, only=("falloff_shape",) if rev >= 3 else None)
                temp.libraries.write(path, {brush}, path_remap='NONE', fake_user=True, compress=True)
        except (OSError, RuntimeError, ReferenceError, AttributeError, TypeError) as e:
            print("Sculpt Fund: brush upgrade %s:" % name, e)


def ensure_brush_library():
    root = brush_dir()
    sub = os.path.join(root, "Saved", "Brushes")
    os.makedirs(sub, exist_ok=True)
    cats = os.path.join(root, "blender_assets.cats.txt")
    if not os.path.exists(cats):
        with open(cats, "w", encoding="utf-8") as f:
            f.write("VERSION 1\n\n%s:%s:%s\n" % (CATALOG_ID, CATALOG, CATALOG))
    essentials = os.path.join(bpy.utils.system_resource('DATAFILES'), ESSENTIALS_FILE)
    for name in BRUSHES:
        path = os.path.join(sub, brush_file(name))
        if os.path.exists(path):
            continue
        with bpy.data.libraries.load(essentials, link=False) as (_src, dst):
            dst.brushes = [name]
        b = dst.brushes[0]
        if b is None:
            continue
        b.name = name
        b.use_pressure_size = True
        apply_brush_defaults(b, name)
        if b.asset_data is None:
            b.asset_mark()
        b.asset_data.catalog_id = CATALOG_ID
        if b.name == name:
            bpy.data.libraries.write(path, {b}, path_remap='NONE', fake_user=True, compress=True)
        bpy.data.brushes.remove(b)
    upgrade_brush_assets(sub)
    libs = bpy.context.preferences.filepaths.asset_libraries
    lib = next((l for l in libs if l.name == LIB_NAME), None)
    if lib is None:
        bpy.ops.preferences.asset_library_add(directory=root)
        libs[-1].name = LIB_NAME
    elif os.path.normcase(os.path.normpath(lib.path)) != os.path.normcase(os.path.normpath(root)):
        lib.path = root


def remove_brush_library():
    prefs_fp = bpy.context.preferences.filepaths
    for i, lib in enumerate(prefs_fp.asset_libraries):
        if lib.name == LIB_NAME:
            bpy.ops.preferences.asset_library_remove(index=i)
            break


def deferred_setup():
    if _pivot.get("follow_shutdown", False):
        return None         # аддон выключили раньше, чем сработал таймер: не трогать раскладку и интерфейс
    try:
        import numpy  # noqa: F401  прогрев: первый импорт ~0,5 с, пусть будет при запуске, а не на первом Ctrl+Shift+клике
    except Exception:
        pass
    try:
        ensure_brush_library()
    except Exception as e:
        print("Sculpt Fund: brushes:", e)
    try:
        user_keymap_apply(prefs().controls_on)
    except Exception as e:
        print("Sculpt Fund: keymap:", e)
    queue_focus_update()
    return None


# --- регистрация ----------------------------------------------------------------------------------------

classes = (
    SCULPTFUND_Preferences,
    SCULPTFUND_OT_toggle, SCULPTFUND_OT_canvas, SCULPTFUND_OT_mask_click, SCULPTFUND_OT_gesture,
    SCULPTFUND_OT_set_ctrl_tool, SCULPTFUND_OT_cs_click,
    SCULPTFUND_OT_set_cs_tool, SCULPTFUND_OT_polyframe, SCULPTFUND_OT_subdiv_level, SCULPTFUND_OT_divide,
    SCULPTFUND_OT_group_masked, SCULPTFUND_OT_replace_mesh, SCULPTFUND_OT_replace_primitive,
    SCULPTFUND_OT_add_mesh_object, SCULPTFUND_OT_add_primitive, SCULPTFUND_OT_split_masked_mesh,
    SCULPTFUND_OT_split_masked, SCULPTFUND_OT_merge_down, SCULPTFUND_OT_symmetrize_side,
    SCULPTFUND_OT_delete_hidden_mesh, SCULPTFUND_OT_delete_hidden, SCULPTFUND_MT_quick,
    SCULPTFUND_MT_primitive_pie, SCULPTFUND_MT_primitive_menu, SCULPTFUND_MT_cs_pie, SCULPTFUND_MT_cs_menu,
    SCULPTFUND_MT_ctrl_pie, SCULPTFUND_MT_ctrl_menu,
    SCULPTFUND_OT_frame, SCULPTFUND_PT_panel,
    SCULPTFUND_OT_gizmo_tool, SCULPTFUND_OT_xform_key, SCULPTFUND_OT_pivot_unmasked, SCULPTFUND_OT_gizmo_world, SCULPTFUND_OT_gizmo_moved,
    SCULPTFUND_OT_pivot_surface, SCULPTFUND_OT_gizmo_press, SCULPTFUND_OT_gizmo_alt, SCULPTFUND_OT_gizmo_scale,
    SCULPTFUND_OT_dup_unmasked, SCULPTFUND_OT_dup_move, SCULPTFUND_OT_zb_grab,
    SCULPTFUND_GGT_gizmo_icons, SCULPTFUND_MT_polygroups_pie,
    SCULPTFUND_OT_brush_popup, SCULPTFUND_GT_brush_tile, SCULPTFUND_GGT_brush_launcher,
    SCULPTFUND_OT_voxel_remesh, SCULPTFUND_OT_voxel_remesh_mesh, SCULPTFUND_OT_dyna_popup,
    SCULPTFUND_OT_alt_click, SCULPTFUND_OT_alt_select,
    SCULPTFUND_OT_symmetry, SCULPTFUND_OT_history, SCULPTFUND_OT_scale, SCULPTFUND_OT_backface_mask,
    SCULPTFUND_OT_mod_hint,
)
HANDLERS = ((bpy.app.handlers.undo_post, _on_undo), (bpy.app.handlers.redo_post, _on_redo),
            (bpy.app.handlers.undo_pre, _on_undo_pre), (bpy.app.handlers.redo_pre, _on_undo_pre),
            (bpy.app.handlers.load_pre, _on_load_pre), (bpy.app.handlers.load_post, _on_load),
            (bpy.app.handlers.save_pre, _on_save_pre), (bpy.app.handlers.save_post, _on_save_post),
            (bpy.app.handlers.depsgraph_update_post, queue_focus_update),
            (bpy.app.handlers.depsgraph_update_post, _dim_updates))
LEGACY_HANDLER_NAMES = ("_on_undo_redo",)      # из 1.2 — снимать при перезагрузке аддона без перезапуска


def register():
    _pivot["follow_shutdown"] = False
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Object.sculpt_fund_dynamesh = BoolProperty(
        name="DynaMesh", default=True,
        description="Как в ZBrush: пустая Ctrl-рамка без маски делает Voxel Remesh (с маской — сбрасывает маску). "
                    "Плотность — Resolution рядом (или Voxel Size в панели N)")
    bpy.types.Object.sculpt_fund_dyna_res = IntProperty(
        name="DynaMesh Resolution", min=4, max=8192, soft_min=16, soft_max=1024, get=_dyna_res_get, set=_dyna_res_set,
        description="Плотность DynaMesh, как Resolution в ZBrush: вокселей по наибольшей стороне объекта. "
                    "Это тот же Voxel Size меша (размер / разрешение)")
    bpy.types.VIEW3D_HT_tool_header.prepend(draw_header)
    register_keymaps()
    set_handlers(True)      # срабатывают только на Ctrl+Z / Ctrl+Shift+Z и загрузку файла, не постоянно
    register_focus()
    register_remesh_panels()
    bpy.app.timers.register(deferred_setup, first_interval=0.5)


def set_handlers(add):
    for lst, fn in HANDLERS:    # по имени: после перезагрузки аддона старые функции — другие объекты
        names = (fn.__name__,) + LEGACY_HANDLER_NAMES
        for h in [h for h in lst if getattr(h, "__name__", "") in names
                  and getattr(h, "__module__", "") == fn.__module__]:
            lst.remove(h)
        if add:
            lst.append(fn)


def unregister():
    _pivot["follow_shutdown"] = True
    _pivot["orient_epoch"] = _pivot.get("orient_epoch", 0) + 1
    unregister_remesh_panels()
    unregister_focus()
    try:
        user_keymap_apply(False)
    except Exception as e:
        print("Sculpt Fund: keymap revert:", e)
    try:
        remove_brush_library()
    except Exception as e:
        print("Sculpt Fund: library:", e)
    unregister_keymaps()
    set_handlers(False)
    if _view_msg["handle"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_view_msg["handle"], 'WINDOW')
        except (ValueError, RuntimeError):
            pass
        _view_msg["handle"] = None
    for timer in (_resync_pivot, _restore_orientation, deferred_setup, _run_history, _end_view_msg):
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)
    _history_queue.clear()
    _orient_hist.clear()
    for h in list(_gesture_handles) + [d["handle"] for d in (_ghost, _scale_line, _scale_ui)
                                       if d["handle"] is not None]:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(h, 'WINDOW')
        except (ValueError, RuntimeError):
            pass
    _gesture_handles.clear()
    _ghost["handle"] = _scale_line["handle"] = _scale_ui["handle"] = None
    bpy.types.VIEW3D_HT_tool_header.remove(draw_header)
    del bpy.types.Object.sculpt_fund_dynamesh
    del bpy.types.Object.sculpt_fund_dyna_res
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
