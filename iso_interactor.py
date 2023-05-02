from vtkmodules.vtkInteractionStyle import vtkInteractorStyleUser
from vtkmodules.vtkRenderingCore import vtkCellPicker, vtkPointPicker, vtkColorTransferFunction
import paraview.servermanager
import paraview.simple
from collections import namedtuple
import sys
import numpy as np
class _State : 
    def __init__(self, function, observer): 
        self.function = function 
        self.observer = observer

color_space = {'RGB' : 0, 'HSV' : 1, 'CIELAB' : 2, 'Diverging' : 3, 'Step' : 4}

if 'interactor' not in sys.modules : #if we are in normal mode 
    print('iso_interactor is on')
    basic_interactor = paraview.servermanager.GetRenderView().GetInteractor().GetInteractorStyle()

    def leftDown(arg1, arg2):
        (x, y) = arg1.GetInteractor().GetEventPosition()
        
        ren = paraview.servermanager.GetRenderView().GetRenderer()
        array_name = paraview.simple.GetDisplayProperties().ColorArrayName[1]
        mode = paraview.simple.GetDisplayProperties().ColorArrayName[0]
        if mode == 'CELLS' : 
            cellPicker = vtkCellPicker()
            cellPicker.Pick(x,y,0,ren)
            cell_id = cellPicker.GetCellId() 
            block_index = cellPicker.GetFlatBlockIndex()
            act = cellPicker.GetActors()
            if act.GetItemAsObject(0) == None : #click outside the figure 
                return None
            map = act.GetItemAsObject(0).GetMapper()
            block = map.GetInputDataObject(0,0).GetBlock(block_index-1)  
            value_index = map.GetLookupTable().GetVectorComponent()
            vector_mode = map.GetLookupTable().GetVectorMode()
            if map.GetLookupTable().GetVectorMode() == 0 :
                tupl = block.GetCellData().GetArray(array_name).GetTuple(cell_id)
                new_value = np.linalg.norm(tupl)
            elif map.GetLookupTable().GetVectorMode() == 1 :  
                new_value = block.GetCellData().GetArray(array_name).GetTuple(cell_id)[value_index]

        elif mode == 'POINTS' : 
            pointPicker = vtkPointPicker()
            pointPicker.Pick(x,y,0,ren)
            point_id = pointPicker.GetPointId() 
            block_index = pointPicker.GetFlatBlockIndex()
            act = pointPicker.GetActors()
            if act.GetItemAsObject(0) == None : #click outside the figure 
                return None
            map = act.GetItemAsObject(0).GetMapper()
            block = map.GetInputDataObject(0,0).GetBlock(block_index-1)  
            value_index = map.GetLookupTable().GetVectorComponent()
            vector_mode = map.GetLookupTable().GetVectorMode()
            if map.GetLookupTable().GetVectorMode() == 0 :
                tupl = block.GetPointData().GetArray(array_name).GetTuple(point_id)
                new_value = np.linalg.norm(tupl)
            elif map.GetLookupTable().GetVectorMode() == 1 :  
                new_value = block.GetPointData().GetArray(array_name).GetTuple(point_id)[value_index]

        m = paraview.simple.GetColorTransferFunction(paraview.simple.GetDisplayProperties().ColorArrayName[1])

        # we create a new color transfert object which is a copy of the original one, so we can add the new color in it after
        color_transfer_object = vtkColorTransferFunction()
        color_transfer_object.SetColorSpace(color_space[m.ColorSpace.GetElement(0)])
        for i in range(int(len(m.RGBPoints)/4)) : 
            color_transfer_object.AddRGBPoint(m.RGBPoints[(i*4)], m.RGBPoints[(i*4) +1], m.RGBPoints[(i*4) +2], m.RGBPoints[(i*4) +3])

        m.Discretize = 0
        m.ColorSpace = 'Step'
        tab = m.RGBPoints
        nb_points = int(len(tab)/4)
        list_values = [tab[i*4] for i in range(nb_points)]
        if new_value not in list_values : 
            list_new_values = list_values + [new_value]
            list_new_values.sort()
            new_tab = [0]*(len(tab) + 4)
            s = 0
            for i in range(nb_points+1) : 
                if list_new_values[i] in list_values : 
                    for j in range(4):
                        new_tab[i*4 + j] = tab[s*4 + j]
                    s += 1
                else : 
                    new_tab[i*4] = new_value 
                    rgb = color_transfer_object.GetColor(new_value)
                    for j in range(3) : 
                        new_tab[(i*4) + j+1] = rgb[j]
        else : 
            new_tab = tab
        m.RGBPoints = new_tab
        paraview.simple.Render()

    # If we don't put the function leftDown into sys.modules, Paraview deletes it and it crashes.
    sys.modules['interactor'] = _State(leftDown, None) 

    import interactor

    #We add the new observer to create the iso
    #we keep the variable returned by AddObserver so we will be able to go back in basic mode later 
    interactor.observer = basic_interactor.AddObserver("LeftButtonPressEvent", interactor.function)


else: #to go back in normal mode 
    print('iso_interactor is off')
    import interactor #we import the variable that we saved before 
    basic_interactor = paraview.servermanager.GetRenderView().GetInteractor().GetInteractorStyle()
    basic_interactor.RemoveObserver(interactor.observer)
    del sys.modules['interactor'] #we have to delete the key in sys.modules so we can create it again if we want to.
