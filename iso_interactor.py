import sys
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleUser
from vtkmodules.vtkRenderingCore import (
    vtkCellPicker,
    vtkPointPicker,
    vtkColorTransferFunction,
)
import paraview.servermanager
import paraview.simple
import numpy as np


class _State:
    def __init__(self, function, observer):
        self.function = function
        self.observer = observer


COLOR_SPACE = {"RGB": 0, "HSV": 1, "CIELAB": 2, "Diverging": 3, "Step": 4, "Lab": 5}


def new_val_cell(x, y, array_name, ren):
    cell_picker = vtkCellPicker()
    cell_picker.Pick(x, y, 0, ren)
    cell_id = cell_picker.GetCellId()
    block_index = cell_picker.GetFlatBlockIndex()
    act = cell_picker.GetActors()
    if act.GetItemAsObject(0) is None:  # click outside the figure
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


def new_val_point(x, y, array_name, ren):
    point_picker = vtkPointPicker()
    point_picker.Pick(x, y, 0, ren)
    point_id = point_picker.GetPointId()
    block_index = point_picker.GetFlatBlockIndex()
    act = point_picker.GetActors()
    if act.GetItemAsObject(0) is None:  # click outside the figure
        return None
    mapper = act.GetItemAsObject(0).GetMapper()
    block = mapper.GetInputDataObject(0, 0).GetBlock(block_index - 1)
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
    # we create a new color transfert function which is a copy of the original one, so we can
    # add the new color in it after
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


def left_button_press_event(arg1, arg2):
    arg1.OnLeftButtonDown()
    x, y = arg1.GetInteractor().GetEventPosition()
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
    add_val_in_color_transfert_function(new_value, color_func_proxy)


if "interactor" not in sys.modules:  # if we are in normal mode
    print("iso_interactor is on")
    basic_interactor = (
        paraview.servermanager.GetRenderView().GetInteractor().GetInteractorStyle()
    )
    # If we don't put the function left_button_press_event into sys.modules,
    # Paraview deletes it and it crashes.
    sys.modules["interactor"] = _State(left_button_press_event, None)

    import interactor

    # We add the new observer to create the iso
    # we keep the variable returned by AddObserver so we will be able to go back in basic mode later
    interactor.observer = basic_interactor.AddObserver(
        "LeftButtonPressEvent", interactor.function
    )

else:  # to go back in normal mode
    print("iso_interactor is off")
    import interactor  # we import the variable that we saved before

    basic_interactor = (
        paraview.servermanager.GetRenderView().GetInteractor().GetInteractorStyle()
    )
    basic_interactor.RemoveObserver(interactor.observer)
    # we have to delete the key in sys.modules so we can create it again if we want to.
    del sys.modules["interactor"]
    