import sys
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleUser
from vtkmodules.vtkCommonCore import vtkIdList
from vtkmodules.vtkRenderingCore import vtkCellPicker, vtkColorTransferFunction
import paraview.servermanager
import paraview.simple
import numpy as np


class _State:
    def __init__(self, function, observer):
        self.function = function
        self.observer = observer


COLOR_SPACE = {"RGB": 0, "HSV": 1, "CIELAB": 2, "Diverging": 3, "Step": 4, "Lab": 5}


def new_val_cell(x, y, array_name, ren):
    """Return a new value for a picked cell in CELLS mode."""
    cell_picker = vtkCellPicker()
    cell_picker.Pick(x, y, 0, ren)
    cell_id = cell_picker.GetCellId()
    block_index = cell_picker.GetFlatBlockIndex()
    act = cell_picker.GetActors()
    # Click outside the figure:
    if act.GetItemAsObject(0) is None:
        return None
    mapper = act.GetItemAsObject(0).GetMapper()
    block = mapper.GetInputDataObject(0, 0).GetBlock(block_index - 1)
    value_index = mapper.GetLookupTable().GetVectorComponent()
    if mapper.GetLookupTable().GetVectorMode() == 0:
        tupl = block.GetCellData().GetArray(array_name).GetTuple(cell_id)
        new_value = np.linalg.norm(tupl)
    elif mapper.GetLookupTable().GetVectorMode() == 1:
        new_value = (
            block.GetCellData().GetArray(array_name).GetTuple(cell_id)[value_index]
        )
    return new_value


def get_point_id(block, cell_id):
    """Return a list with all the points ids which belongs to the clicked cell."""
    list_points_id = []
    pts_ids = vtkIdList()
    block.GetCellPoints(cell_id, pts_ids)
    nb_pts = pts_ids.GetNumberOfIds()
    for i in range(nb_pts):
        list_points_id.append(pts_ids.GetId(i))
    return list_points_id


def get_nearest_point(list_points_id, cell_picker, block):
    """Return the id of the nearest point of the picked cell."""
    coord_picked_point = np.array(cell_picker.GetPickPosition())
    dists = []
    for pt_id in list_points_id:
        coord_pt = np.array(block.GetPoint(pt_id))
        dists.append(np.linalg.norm(coord_picked_point - coord_pt))
    point_id = list_points_id[np.array(dists).argmin()]
    return point_id


def new_val_point(x, y, array_name, ren):
    """To find a new value in POINTS mode we can not use the point picker
    because it returns a wrong point id : we use a cell picker and we
    are going to find the right point id from this cell picker."""
    cell_picker = vtkCellPicker()
    cell_picker.Pick(x, y, 0, ren)
    cell_id = cell_picker.GetCellId()
    block_index = cell_picker.GetFlatBlockIndex()
    act = cell_picker.GetActors()
    if act.GetItemAsObject(0) is None:  # click outside the figure
        return None
    mapper = act.GetItemAsObject(0).GetMapper()
    block = mapper.GetInputDataObject(0, 0).GetBlock(block_index - 1)
    # We have to find the points which belongs to the clicked cell:
    list_points_id = get_point_id(block, cell_id)
    # Then we choose the nearest point of the picked cell:
    point_id = get_nearest_point(list_points_id, cell_picker, block)
    value_index = mapper.GetLookupTable().GetVectorComponent()
    if mapper.GetLookupTable().GetVectorMode() == 0:
        tupl = block.GetPointData().GetArray(array_name).GetTuple(point_id)
        new_value = np.linalg.norm(tupl)
    elif mapper.GetLookupTable().GetVectorMode() == 1:
        new_value = (
            block.GetPointData().GetArray(array_name).GetTuple(point_id)[value_index]
        )
    return new_value


def add_val_in_color_transfert_function(new_value, color_func_proxy):
    """We add the new value and the associated color (found into the proxy)
    into the color transfert function."""
    # We create a new color transfert function which is a copy of the original
    # one, so we can add the new color in it after:
    color_func = vtkColorTransferFunction()
    color_func.SetColorSpace(COLOR_SPACE[color_func_proxy.ColorSpace.GetElement(0)])
    for i in range(int(len(color_func_proxy.RGBPoints) / 4)):
        color_func.AddRGBPoint(
            color_func_proxy.RGBPoints[(i * 4)],
            color_func_proxy.RGBPoints[(i * 4) + 1],
            color_func_proxy.RGBPoints[(i * 4) + 2],
            color_func_proxy.RGBPoints[(i * 4) + 3],
        )
    color_func_proxy.Discretize = 0
    color_func_proxy.ColorSpace = "Step"
    tab = color_func_proxy.RGBPoints
    nb_points = int(len(tab) / 4)
    list_values = [tab[i * 4] for i in range(nb_points)]
    if new_value not in list_values:
        list_new_values = list_values + [new_value]
        list_new_values.sort()
        new_tab = [0] * (len(tab) + 4)
        s = 0
        for i in range(nb_points + 1):
            if list_new_values[i] in list_values:
                for j in range(4):
                    new_tab[i * 4 + j] = tab[s * 4 + j]
                s += 1
            else:
                new_tab[i * 4] = new_value
                rgb = color_func.GetColor(new_value)
                for j in range(3):
                    new_tab[(i * 4) + j + 1] = rgb[j]
    else:
        new_tab = tab
    color_func_proxy.RGBPoints = new_tab
    paraview.simple.Render()


def left_button_press_event(interactor_style, event):
    """Describe what happend when we press the left button of the mouse."""
    # We keep the initial functionalities of the event:
    interactor_style.OnLeftButtonDown()
    x, y = interactor_style.GetInteractor().GetEventPosition()
    ren = paraview.servermanager.GetRenderView().GetRenderer()
    array_name = paraview.simple.GetDisplayProperties().ColorArrayName[1]
    mode = paraview.simple.GetDisplayProperties().ColorArrayName[0]
    if mode == "CELLS":
        new_value = new_val_cell(x, y, array_name, ren)
    elif mode == "POINTS":
        new_value = new_val_point(x, y, array_name, ren)
    color_func_proxy = paraview.simple.GetColorTransferFunction(
        paraview.simple.GetDisplayProperties().ColorArrayName[1]
    )
    if new_value is None:
        return None
    add_val_in_color_transfert_function(new_value, color_func_proxy)


if "interactor" not in sys.modules:  # if we are in normal mode
    print("iso_interactor is on")
    basic_interactor = (
        paraview.servermanager.GetRenderView().GetInteractor().GetInteractorStyle()
    )
    # If we don't put the function left_button_press_event into sys.modules,
    # Paraview deletes it and it crashes:
    sys.modules["interactor"] = _State(left_button_press_event, None)

    import interactor

    # We add the new observer to create the iso and we keep the variable
    # returned by AddObserver so we will be able to go back in basic mode later:
    interactor.observer = basic_interactor.AddObserver(
        "LeftButtonPressEvent", interactor.function
    )

else:  # to go back in normal mode
    print("iso_interactor is off")
    # We import the variable that we saved before:
    import interactor

    basic_interactor = (
        paraview.servermanager.GetRenderView().GetInteractor().GetInteractorStyle()
    )
    basic_interactor.RemoveObserver(interactor.observer)
    # We have to delete the key in sys.modules so we can create it again if we want to:
    del sys.modules["interactor"]
