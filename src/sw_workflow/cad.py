"""Serial STA SolidWorks backend. Imported only after explicit CAD preflight.

Only documents created or opened by this job may be changed or closed. The
writer lock belongs to the service; native calls are never automatically retried.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import math
import os

import pythoncom
from win32com.client import VARIANT, dynamic

from ._vendor.sw_connect import (
    connect_solidworks, create_empty_dispatch_variant, find_template,
    get_com_member as member, get_sw_version, save_document,
)
from ._vendor import sw_part as part
from ._vendor.sw_export import export_to_step
from .evidence import check, unique_cylinders
from .guard import GuardError
from .spec import PartSpec


def require(value, message):
    if value is None or value is False:
        raise GuardError(message)
    return value


def same_path(a, b):
    return os.path.normcase(str(Path(a).resolve())) == os.path.normcase(str(Path(b).resolve()))


class Session:
    def __enter__(self):
        pythoncom.CoInitialize()
        self.owned = []
        self.preferences = []
        self.prior = None
        try:
            self.sw, self.prior = connect_solidworks(wait_seconds=45)
            # Dynamic dispatch preserves explicit by-reference output arguments.
            self.sw = dynamic.DumbDispatch(self.sw._oleobj_, "SldWorks.Application")
            self.version = get_sw_version(self.sw)
            if self.prior is not None:
                self.prior_title = member(self.prior, "GetTitle")
            self.toggle(10, False)  # swInputDimValOnCreate: restore on exit.
            return self
        except BaseException:
            for key, value in reversed(self.preferences):
                self.sw.SetUserPreferenceToggle(key, value)
            pythoncom.CoUninitialize()
            raise

    def toggle(self, key, value):
        old = self.sw.GetUserPreferenceToggle(key)
        self.preferences.append((key, old))
        self.sw.SetUserPreferenceToggle(key, value)
        require(self.sw.GetUserPreferenceToggle(key) == value, "Cannot set temporary CAD preference")

    def new(self, kind="part"):
        template = os.environ.get("SW_WORKFLOW_" + kind.upper() + "_TEMPLATE") or find_template(self.sw, kind)
        model = require(self.sw.NewDocument(str(Path(template).resolve()), 0, 0., 0.), "NewDocument returned no document")
        self.owned.append(model)
        model.SetUnits(0, 0, 0, 3, False)  # millimetres, decimal display
        if kind=='part' and len(member(model,'GetConfigurationNames') or ())!=1:
            raise GuardError('Use a single-configuration part template for this release')
        return model

    def open(self, path: Path, foreign=False):
        opened = tuple(member(self.sw,'GetDocuments') or ())
        conflict = any(str(member(doc,'GetTitle')).casefold() in {path.name.casefold(),path.stem.casefold()} for doc in opened)
        if self.sw.GetOpenDocumentByName(str(path)) is not None or conflict:
            raise GuardError("The target is already open; close this workflow artifact before retrying")
        errors = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        warnings = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        if foreign:
            # LoadFile4 uses the default part template. Never persist a changed default.
            before = self.sw.GetUserPreferenceStringValue(8)
            toggle = self.sw.GetUserPreferenceToggle(111)
            template = os.environ.get("SW_WORKFLOW_PART_TEMPLATE") or find_template(self.sw, "part")
            try:
                self.sw.SetUserPreferenceStringValue(8, template)
                self.sw.SetUserPreferenceToggle(111, True)
                data = require(self.sw.GetImportFileData(str(path)), "Cannot get STEP import options")
                model = self.sw.LoadFile4(str(path), "r", data, errors)
            finally:
                self.sw.SetUserPreferenceStringValue(8, before)
                self.sw.SetUserPreferenceToggle(111, toggle)
        else:
            doc_type = 3 if path.suffix.lower() == ".slddrw" else 1
            model = self.sw.OpenDoc6(str(path), doc_type, 1, "", errors, warnings)
        require(model, f"Document open failed (code {errors.value})")
        self.owned.append(model)
        if errors.value:
            raise GuardError(f"Document open reported errors ({errors.value})")
        return model

    def expect(self, model, path: Path | None = None):
        if not any(m is model for m in self.owned):
            raise GuardError("Document is not owned by this job")
        actual = member(model, "GetPathName")
        if path is not None and (not actual or not same_path(actual, path)):
            raise GuardError("Document path changed during the job")
        title = member(model, "GetTitle")
        errors = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        active = self.sw.ActivateDoc3(actual or title, False, 0, errors)
        require(active, "Cannot activate the owned document")
        if errors.value:
            raise GuardError(f"Document activation failed ({errors.value})")
        if member(active, "GetTitle") != title:
            raise GuardError("Unexpected active document")
        if path is not None and not same_path(member(active, "GetPathName"), path):
            raise GuardError("Unexpected active document path")

    def close(self, model):
        if not any(m is model for m in self.owned):
            raise GuardError("Refusing to close a document not owned by this job")
        self.sw.CloseDoc(member(model, "GetTitle"))
        self.owned = [m for m in self.owned if m is not model]

    def __exit__(self, exc_type, exc, tb):
        failures = []
        try:
            for model in list(reversed(self.owned)):
                try:
                    self.close(model)
                except Exception:
                    failures.append("owned document close")
            for key, value in reversed(self.preferences):
                try:
                    self.sw.SetUserPreferenceToggle(key, value)
                    require(self.sw.GetUserPreferenceToggle(key) == value, "Preference restore failed")
                except Exception:
                    failures.append("preference restoration")
            if self.prior is not None:
                try:
                    errors = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                    require(self.sw.ActivateDoc3(self.prior_title, False, 0, errors), "Prior document restore failed")
                except Exception:
                    failures.append("previous active document restoration")
        finally:
            part._SKETCH_SELECTION_CACHE.clear()
            self.owned.clear()
            pythoncom.CoUninitialize()
        if failures:
            raise GuardError("Session cleanup needs attention: " + ", ".join(failures)) from exc


class TemplateBuilder:
    def __init__(self, model, spec: PartSpec, checkpoint: Path | None = None):
        self.model, self.spec = model, spec
        self.checkpoint = checkpoint
        self.bindings = {}
        self.sketches = []

    @contextmanager
    def profile(self, name):
        part.start_sketch(self.model)
        sketch = member(self.model.SketchManager, "ActiveSketch")
        feature = require(self.model.FeatureByPositionReverse(0), "Active profile feature missing")
        if member(feature, "GetTypeName2") != "ProfileFeature":
            raise GuardError("Newest feature is not the owned sketch")
        feature.Name = name
        self.sketches.append(name)
        try:
            yield sketch
        finally:
            part.end_sketch(self.model)

    def select(self, *objects):
        self.model.ClearSelection2(True)
        for i, obj in enumerate(objects):
            require(bool(obj.Select4(i > 0, create_empty_dispatch_variant())), "Sketch entity selection failed")

    def fix(self, point):
        self.select(point)
        self.model.SketchAddConstraints("sgFIXED")

    def dimension(self, name, expression, method, objects, position):
        self.select(*objects)
        display = require(getattr(self.model, method)(*position, 0.), "Dimension creation failed")
        dim = display.GetDimension2(0)
        dim.Name = name
        # FullName also contains the current document title; equations use two fields.
        path = "@".join(str(dim.FullName).split("@")[:2])
        self.bindings[path] = expression

    def rectangle(self, name, width_key, height_key):
        p = self.spec.parameters
        w, h = p[width_key] / 1000, p[height_key] / 1000
        with self.profile(name):
            lines = require(self.model.SketchManager.CreateCornerRectangle(0., 0., 0., w, h, 0.), "Rectangle failed")
            # Fix only the origin. Sides remain controlled by native dimensions.
            origin = min((member(line, "GetStartPoint2") for line in lines), key=lambda q: q.X*q.X + q.Y*q.Y)
            self.fix(origin)
            horizontal = next(line for line in lines if abs(member(line, "GetStartPoint2").Y - member(line, "GetEndPoint2").Y) < 1e-10)
            vertical = next(line for line in lines if abs(member(line, "GetStartPoint2").X - member(line, "GetEndPoint2").X) < 1e-10)
            self.dimension("Width", f'"{width_key}"', "AddHorizontalDimension2", [horizontal], (w/2, -h/4))
            self.dimension("Height", f'"{height_key}"', "AddVerticalDimension2", [vertical], (-w/4, h/2))

    def boss(self, profile, name, key):
        feat = require(part.extrude_boss(self.model, profile, self.spec.parameters[key] / 1000, direction=False), "Boss failed")
        feat.Name = name
        require(self.model.Parameter("D1@" + name), "Extrusion depth dimension missing")
        self.bindings["D1@" + name] = f'"{key}"'
        if self.checkpoint is not None:
            require(save_document(self.model,str(self.checkpoint)), 'Native checkpoint failed')

    def circles(self):
        p = self.spec.parameters
        with self.profile("Holes"):
            if self.spec.template == "bushing":
                for name, key in (("Outer", "outer_diameter"), ("Inner", "inner_diameter")):
                    arc = require(self.model.SketchManager.CreateCircleByRadius(0., 0., 0., p[key]/2000), "Circle failed")
                    self.fix(member(arc, "GetCenterPoint2"))
                    self.dimension(name, f'"{key}"', "AddDiameterDimension2", [arc], (p[key]/1500, p[key]/1500))
            else:
                origin = require(self.model.SketchManager.CreatePoint(0., 0., 0.), "Reference point failed")
                self.fix(origin)
                for i, (x, y, ex, ey) in enumerate(hole_targets(self.spec), 1):
                    arc = require(self.model.SketchManager.CreateCircleByRadius(x/1000, y/1000, 0., p['hole_diameter']/2000), "Hole circle failed")
                    center = member(arc, "GetCenterPoint2")
                    self.dimension(f"Hole{i}D", '"hole_diameter"', "AddDiameterDimension2", [arc], (x/1000+.01, y/1000+.01))
                    self.dimension(f"Hole{i}X", ex, "AddHorizontalDimension2", [origin, center], (x/2000, -.01*i))
                    self.dimension(f"Hole{i}Y", ey, "AddVerticalDimension2", [origin, center], (-.01*i, y/2000))

    def build(self):
        kind = self.spec.template
        if kind == "bushing":
            self.circles()
            self.boss("Holes", "Sleeve", "length")
        else:
            self.rectangle("BaseProfile", "width", "height" if kind == "plate" else "thickness")
            self.boss("BaseProfile", "Base", "thickness" if kind == "plate" else "depth")
            if kind == "plate":
                self.circles()
                part._ensure_sketch_selected(self.model, "Holes")
                # Front-plane boss runs in +Z. Cut's Dir is reversed to enter it.
                feat = require(self.model.FeatureManager.FeatureCut4(
                    True, False, True, 1, 0, .01, 0.,
                    False, False, False, False, 0., 0.,
                    False, False, False, False, False,
                    True, True, True, True, False, 0, 0., False, False), "Through holes failed")
                feat.Name = "ThroughHoles"
            else:
                self.rectangle("WallProfile", "width", "height")
                self.boss("WallProfile", "Wall", "thickness")
        equations = member(self.model, "GetEquationMgr")
        for name, value in self.spec.parameters.items():
            if equations.Add2(-1, f'"wf_{name}" = {value:.12g}mm', True) < 0:
                raise GuardError("Global variable creation failed: " + name)
        for path, expr in self.bindings.items():
            for name in self.spec.parameters:
                expr = expr.replace(f'"{name}"', f'"wf_{name}"')
            if equations.Add2(-1, f'"{path}" = {expr}', True) < 0:
                raise GuardError("Dimension binding failed: " + path)
        member(equations, "EvaluateAll")
        require(bool(member(self.model, "EditRebuild3")), "Parametric rebuild failed")
        return {"bindings": self.bindings, "sketches": self.sketches}


def hole_targets(spec):
    p = spec.parameters
    result = []
    for x, ex in ((p['margin_x'], '"margin_x"'), (p['width']-p['margin_x'], '"width" - "margin_x"')):
        for y, ey in ((p['margin_y'], '"margin_y"'), (p['height']-p['margin_y'], '"height" - "margin_y"')):
            result.append((x, y, ex, ey))
    return result


def update_globals(model, spec):
    equations = member(model, "GetEquationMgr")
    index_by_name = {}
    for i in range(member(equations, "GetCount")):
        lhs = str(equations.Equation(i)).split("=", 1)[0].strip().strip('"')
        if lhs.startswith('wf_'):
            index_by_name[lhs[3:]] = i
    if set(spec.parameters) - set(index_by_name):
        raise GuardError("Managed global variables are missing")
    dispid = equations._oleobj_.GetIDsOfNames("Equation")
    for name, value in spec.parameters.items():
        equations._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, 0,
                                 index_by_name[name], f'"wf_{name}" = {value:.12g}mm')
    member(equations, "EvaluateAll")
    require(bool(member(model, "EditRebuild3")), "Updated model could not rebuild")


def measure(model):
    bodies = tuple(model.GetBodies2(0, False) or ())
    if not bodies:
        return {"body_count": 0, "volume_mm3": 0., "extents_mm": [], "cylinders": []}
    lows, highs = [], []
    for axis in range(3):
        direction = [0., 0., 0.]
        direction[axis] = 1.
        maximum = [b.GetExtremePoint(*direction, 0., 0., 0.) for b in bodies]
        direction[axis] = -1.
        minimum = [b.GetExtremePoint(*direction, 0., 0., 0.) for b in bodies]
        if not all(v[0] for v in maximum + minimum):
            raise GuardError("Exact body extent measurement failed")
        highs.append(max(v[axis+1] for v in maximum) * 1000)
        lows.append(min(v[axis+1] for v in minimum) * 1000)
    mass = require(member(model.Extension, "CreateMassProperty"), "Mass property creation failed")
    cylinders = []
    for body in bodies:
        for face in member(body, "GetFaces") or ():
            surface = member(face, "GetSurface")
            if member(surface, "IsCylinder"):
                params = list(member(surface, "CylinderParams"))
                cylinders.append({"center_xy_mm": [params[0]*1000, params[1]*1000],
                                  "axis": params[3:6], "diameter_mm": 2*params[6]*1000})
    return {"body_count": len(bodies), "volume_mm3": mass.Volume * 1e9,
            "extents_mm": [hi-lo for hi,lo in zip(highs,lows)], "cylinders": cylinders}


def geometry_checks(model, spec):
    actual = measure(model)
    checks = {
        "solid_body_count": check(actual['body_count'] == 1, actual=actual['body_count'], expected=1),
        "volume": check(math.isclose(actual['volume_mm3'], spec.volume_mm3, rel_tol=1e-6, abs_tol=1e-5), actual_mm3=actual['volume_mm3'], expected_mm3=spec.volume_mm3),
        "extents": check(len(actual['extents_mm']) == 3 and all(math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-5) for a,b in zip(actual['extents_mm'], spec.extents_mm)), actual_mm=actual['extents_mm'], expected_mm=spec.extents_mm),
    }
    if spec.template == "plate":
        expected = [(x,y,spec.parameters['hole_diameter']) for x,y,_,_ in hole_targets(spec)]
    elif spec.template == "bushing":
        expected = [(0.,0.,spec.parameters[k]) for k in ('outer_diameter','inner_diameter')]
    else:
        expected = []
    cylinders = unique_cylinders(actual['cylinders'])
    remaining = list(cylinders)
    for x,y,d in expected:
        match = next((c for c in remaining if abs(c['center_xy_mm'][0]-x)<1e-5 and abs(c['center_xy_mm'][1]-y)<1e-5 and abs(c['diameter_mm']-d)<1e-5 and abs(abs(c['axis'][2])-1.)<1e-8), None)
        if match is not None:
            remaining.remove(match)
    checks['cylindrical_geometry'] = check(len(cylinders)==len(expected) and not remaining, actual=cylinders, expected_count=len(expected))
    return checks


def native_checks(model, spec, contract):
    checks = geometry_checks(model, spec)
    units=list(member(model,'GetUnits'))
    checks['native_units']=check(units[0]==0, length_unit=units[0], expected='millimetres')
    errors = []
    feature = member(model, "FirstFeature")
    while feature is not None:
        warning = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BOOL, False)
        code = feature.GetErrorCode2(warning)
        if code or warning.value:
            errors.append({"feature": feature.Name, "code": code, "warning": warning.value})
        feature = member(feature, "GetNextFeature")
    checks['feature_errors'] = check(not errors, issues=errors)
    dimensions = []
    # The expression grammar is intentionally limited; never eval model text.
    for path, expression in contract['bindings'].items():
        terms = expression.replace('"', '').split(' - ')
        expected = spec.parameters[terms[0]] - (spec.parameters[terms[1]] if len(terms)>1 else 0.)
        dim = model.Parameter(path)
        actual = dim.SystemValue * 1000 if dim is not None else None
        dimensions.append({"path": path, "actual_mm": actual, "expected_mm": expected,
                           "pass": actual is not None and math.isclose(actual,expected,rel_tol=1e-7,abs_tol=1e-5)})
    checks['driving_dimensions'] = check(bool(dimensions) and all(d['pass'] for d in dimensions), dimensions=dimensions)
    statuses = []
    for name in contract['sketches']:
        feat = require(model.FeatureByName(name), "Expected sketch is missing")
        sk = require(member(feat, "GetSpecificFeature2"), "Expected sketch data is missing")
        statuses.append({"sketch": name, "constraint_status": member(sk, "GetConstrainedStatus")})
    checks['fully_constrained_sketches'] = check(bool(statuses) and all(s['constraint_status']==3 for s in statuses), sketches=statuses)
    return checks


def finish_part(session, model, folder, name, spec, contract):
    native, step, preview = folder/(name+'.SLDPRT'), folder/(name+'.step'), folder/(name+'.bmp')
    session.expect(model)
    require(save_document(model, str(native)), "Native checkpoint save failed")
    session.expect(model, native)
    checks = native_checks(model, spec, contract)
    model.ShowNamedView2("", 7)
    member(model, "ViewZoomtofit2")
    require(bool(model.SaveBMP(str(preview), 1200, 900)), "Preview export failed")
    require(bool(export_to_step(model, str(step))), "STEP export failed")
    session.close(model)
    reopened = session.open(native)
    session.expect(reopened, native)
    require(bool(member(reopened, "EditRebuild3")), "Reopened model failed to rebuild")
    rechecks = native_checks(reopened, spec, contract)
    checks['reopened_native'] = check(all(c['status']=='pass' for c in rechecks.values()), checks=rechecks)
    session.close(reopened)
    imported = session.open(step, foreign=True)
    step_checks = geometry_checks(imported, spec)
    checks['step_roundtrip'] = check(all(c['status']=='pass' for c in step_checks.values()), checks=step_checks)
    session.close(imported)
    return checks, [native.name, step.name, preview.name]
