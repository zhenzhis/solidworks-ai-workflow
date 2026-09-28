"""Optional native review drawing. Not a manufacturing drawing generator."""
from pathlib import Path
import math
import pythoncom
from win32com.client import VARIANT

from .cad import Session, member, require, same_path
from ._vendor.sw_connect import save_document, create_empty_dispatch_variant
from .evidence import check


def create_review_drawing(folder: Path, name: str, spec):
    native = folder/(name+'.SLDPRT')
    drawing = folder/(name+'.SLDDRW')
    pdf = folder/(name+'.pdf')
    preview = folder/(name+'-drawing.bmp')
    with Session() as session:
        model = session.open(native)
        session.expect(model, native)
        doc = session.new('drawing')
        session.expect(doc)
        sheet = member(doc, 'GetCurrentSheet')
        sheet.SetSize(8, .420, .297)  # A3; sheet units are metres.
        denominator = max(1, math.ceil(max(spec.extents_mm)/75))
        sheet.SetScale(1., float(denominator), False, False)
        # Independent views, deliberately labelled; no projection-standard claim.
        views = []
        locations = []
        for label, aliases, x, y in (
            ('FRONT', ('*Front','*前视'), .105,.190),
            ('TOP', ('*Top','*上视'), .105,.085),
            ('RIGHT', ('*Right','*右视'), .285,.190),
            ('ISOMETRIC', ('*Isometric','*等轴测'), .285,.115),
        ):
            view = None
            for alias in aliases:
                view = doc.CreateDrawViewFromModelView3(str(native), alias, x,y,0.)
                if view is not None:
                    break
            require(view, 'Drawing view creation failed: '+label)
            view.UseSheetScale = True
            views.append(view)
            locations.append((x,y))
        # The first inserted view may trigger SolidWorks automatic scaling.
        # Apply the intended scale after all views exist, then restore centres.
        sheet.SetScale(1., float(denominator), False, False)
        for view,(x,y) in zip(views,locations):
            view.UseSheetScale = True
            view.Position = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (x,y))
        doc.ClearSelection2(True)
        # Actual model dimensions, not text approximations of dimensions.
        require(bool(doc.Extension.SelectByID2(member(views[0],'GetName2'),'DRAWINGVIEW',0.,0.,0.,False,0,create_empty_dispatch_variant(),0)), 'Drawing view selection failed')
        dimensions = tuple(doc.InsertModelAnnotations3(0,32768|524288,True,False,False,False) or ())
        doc.ActivateView('')
        note = require(doc.InsertNote('REVIEW DRAFT - NOT FOR MANUFACTURE\nIndependent FRONT / TOP / RIGHT / ISOMETRIC views. Units: mm.\nTolerances, datums, material and dimension completeness require engineering review.'), 'Draft note failed')
        annotation = member(note, 'GetAnnotation')
        annotation.SetPosition2(.020,.280,0.)
        require(bool(member(doc,'EditRebuild3')), 'Drawing rebuild failed')
        require(save_document(doc,str(drawing)), 'Drawing save failed')
        session.expect(doc,drawing)
        doc.ClearSelection2(True)
        member(doc,'ViewZoomtofit2')
        require(bool(doc.SaveBMP(str(preview),1600,1100)), 'Drawing preview failed')
        # SaveAs with no export object exports the sheet without a PDF viewer.
        require(save_document(doc,str(pdf)), 'PDF export failed')
        session.close(doc)
        reopened = session.open(drawing)
        session.expect(reopened,drawing)
        require(bool(member(reopened,'EditRebuild3')), 'Reopened drawing rebuild failed')
        refs=[]
        outlines=[]
        view=member(reopened,'GetFirstView')
        view=member(view,'GetNextView')  # The first view is the sheet itself.
        while view is not None:
            referenced=member(view,'ReferencedDocument')
            refs.append(referenced is not None and same_path(member(referenced,'GetPathName'),native))
            outlines.append(list(member(view,'GetOutline')))
            view=member(view,'GetNextView')
        on_sheet=all(0.005<=o[0]<o[2]<=.415 and .065<=o[1]<o[3]<=.270 for o in outlines)
        overlap=any(min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
                    for i,a in enumerate(outlines) for b in outlines[i+1:])
        units=list(member(reopened,'GetUnits'))
        result=check(len(refs)==4 and all(refs) and len(dimensions)>0 and on_sheet and not overlap and units[0]==0,
                     native_views=len(refs), referenced_model_resolved=all(refs),
                     view_outlines_m=outlines, views_on_sheet=on_sheet, views_overlap=overlap, length_unit=units[0],
                     imported_model_dimensions=len(dimensions), reopened=True,
                     scope='review drawing only; manufacturing completeness and layout require human review')
    return result,[drawing.name,pdf.name,preview.name]
