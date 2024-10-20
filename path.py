import bpy
from xml.etree import ElementTree
from xml.dom import minidom
from math import pi, inf
from mathutils import Vector
from enum import Enum

precision = 4
target_width = 256
target_height = 256
output_path = 'C:\\Users\\Dylan\\Desktop\\my_svg.svg'

CommandType = Enum('CommandType', ['MoveTo', 'CurveTo', 'ClosePath'])

class MoveTo:
    command_type = CommandType.MoveTo
    pos = None
    
    def __init__(self, pos):
        self.pos = pos
        
    def scale(self, factor):
        self.pos = self.pos * factor
    
    def translate(self, offset):
        self.pos = self.pos + offset
    
    def to_d(self):
        pos = self.pos.to_tuple(precision)
        
        return f'M{pos[0]},{pos[1]}'

class CurveTo:
    command_type = CommandType.CurveTo
    pos = None
    control_1 = None
    control_2 = None
    
    def __init__(self, pos, control_1, control_2):
        self.pos = pos
        self.control_1 = control_1
        self.control_2 = control_2
    
    def scale(self, factor):
        self.pos = self.pos * factor
        self.control_1 = self.control_1 * factor
        self.control_2 = self.control_2 * factor
    
    def translate(self, offset):
        self.pos = self.pos + offset
        self.control_1 = self.control_1 + offset
        self.control_2 = self.control_2 + offset
    
    def to_d(self):
        pos = self.pos.to_tuple(precision)
        control_1 = self.control_1.to_tuple(precision)
        control_2 = self.control_2.to_tuple(precision)
        
        return f'C{control_1[0]},{control_1[1]} {control_2[0]},{control_2[1]} {pos[0]},{pos[1]}'

class ClosePath:
    command_type = CommandType.ClosePath
    def to_d(self):
        return 'Z'

class Bounds:
    min_x = inf
    max_x = -inf
    min_y = inf
    max_y = -inf

def main():
    svg = ElementTree.Element('svg')
    svg.set('xmlns', "http://www.w3.org/2000/svg")
    svg.set('version', "1.1")
    svg.set('stroke', '#000')
    svg.set('fill', 'none')

    all_paths = []
    
    if len(bpy.context.selected_objects) == 0:
        raise ValueError('No objects selected.')
    
    for obj in bpy.context.selected_objects:
        if obj.type != 'CURVE':
            continue
        
        if obj.data.dimensions != '2D':
            raise ValueError('Selected curve(s) are using the incorrect shape.  Shape must be set to 2D.')
        
        obj_scale = obj.scale.to_2d()
        
        if obj.rotation_euler.z != 0 or obj.location.to_2d().length > 0 or obj_scale[0] != 1 or obj_scale[1] != 1:
            raise ValueError('Selected curve(s) have un-applied transformations.  Please apply these first.')

        for spline in obj.data.splines:
            path = []
            prev_handle_2 = None
            
            for point in spline.bezier_points:
                control_point = point.co.to_2d()
                handle_1 = point.handle_left.to_2d()
                handle_2 = point.handle_right.to_2d()
                
                if not path:
                    path.append(MoveTo(control_point))
                else:
                    path.append(CurveTo(control_point, prev_handle_2, handle_1))

                prev_handle_2 = handle_2
                
            if spline.use_cyclic_u:
                # Curve to the beginning point when closing
                first_point = spline.bezier_points[0]
                first_control_point = first_point.co.to_2d()
                first_handle_1 = first_point.handle_left.to_2d()
                
                path.append(CurveTo(first_control_point, prev_handle_2, first_handle_1))
                path.append(ClosePath())
            
            all_paths.append(path)
    
    # Calculate the bounding box for the commands
    bounds = Bounds()
    
    for path in all_paths:
        for command in path:
            if command.command_type == CommandType.MoveTo or command.command_type == CommandType.CurveTo:
                bounds.min_x = min(command.pos[0], bounds.min_x)
                bounds.max_x = max(command.pos[0], bounds.max_x)
                bounds.min_y = min(command.pos[1], bounds.min_y)
                bounds.max_y = max(command.pos[1], bounds.max_y)

    bounds_width = abs(bounds.max_x) - abs(bounds.min_x)
    bounds_height = abs(bounds.max_y) - abs(bounds.min_y)
    
    flip_factor = Vector((1.0, -1.0))
    flip_offset = Vector((0.0, bounds_height))
    base_offset = Vector((-bounds.min_x, -bounds.min_y))
    
    # Determine the scale needed to reach the target dimensions
    scale_factor = min(target_width / bounds_width, target_height / bounds_height)
    
    # Scale and accumulate commands
    for path in all_paths:
        path_data = []
        for command in path:
            if command.command_type == CommandType.MoveTo or command.command_type == CommandType.CurveTo:
                command.translate(base_offset)
                command.scale(flip_factor)
                command.translate(flip_offset)
                command.scale(scale_factor)
            
            path_data.append(command.to_d())
        
        path_element = ElementTree.Element('path')
        path_element.set('d', ' '.join(path_data))
        svg.append(path_element)

    # Scale the bounding dimensions 
    bounds_width = bounds_width * scale_factor
    bounds_height = bounds_height * scale_factor
    
    svg.set('viewBox', f'0 0 {bounds_width} {bounds_height}')
    
    f = open(output_path, 'w')
    f.write(pretty_xml(svg))
    f.close()
    

def pretty_xml(elem):
    """Returns a pretty-printed XML string for the Element"""

    rough_string = ElementTree.tostring(elem, 'unicode')
    reparsed = minidom.parseString(rough_string)
    
    return reparsed.toprettyxml(indent='  ')

if __name__ == '__main__':
    main()
