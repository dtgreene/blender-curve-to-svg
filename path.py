import bpy
from xml.etree import ElementTree
from xml.dom import minidom
from math import pi, inf
from mathutils import Vector
from enum import Enum

precision = 4

# Auto-fit scales and centers the image within the target dimensions including margins
enable_auto_fit = True

# Auto-fit settings
target_width = 256
target_height = 256
x_margin = 10
y_margin = 10

# Absolute output path
output_path = 'C:\\Users\\Dylan\\Downloads\\blender_output.svg'
# The amount to scale all points.  By default, values are in meters so 1000.0 would convert into millimeters.
unit_scale = 1000.0

CommandType = Enum('CommandType', ['MoveTo', 'CurveTo', 'ClosePath', 'LineTo'])

class BaseCommand:
    def scale(self, factor):
        pass

    def translate(self, offset):
        pass

    def to_d(self):
        raise NotImplementedError('to_d() has not been implemented for this command.')
    

class MoveTo(BaseCommand):
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

class LineTo(BaseCommand):
    command_type = CommandType.LineTo
    pos = None
    
    def __init__(self, pos):
        self.pos = pos
        
    def scale(self, factor):
        self.pos = self.pos * factor
    
    def translate(self, offset):
        self.pos = self.pos + offset
    
    def to_d(self):
        pos = self.pos.to_tuple(precision)
        
        return f'L{pos[0]},{pos[1]}'


class CurveTo(BaseCommand):
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

class ClosePath(BaseCommand):
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
            raise ValueError('Selected curve(s) are using the incorrect curve type.  The curve type must be set to 2D.')
        
        obj_scale = obj.scale.to_2d()
        scale_diff = abs(obj_scale[0] - obj_scale[1])
        
        if obj.rotation_euler.z != 0 or obj.location.to_2d().length > 0 or scale_diff > 0.01:
            raise ValueError('Selected curve(s) have un-applied transformations.  Please apply these first.')

        for spline in obj.data.splines:
            match spline.type:
                case 'POLY':
                    all_paths.append(convert_poly(spline))
                case 'BEZIER':
                    all_paths.append(convert_bezier(spline))
                case _:
                    raise ValueError('NURBS spline type is not currently supported.')

    # Scale all points to match the desired units
    for path in all_paths:
        for command in path:
            command.scale(unit_scale)
    
    # Calculate the bounding box for the commands
    bounds = Bounds()
    
    for path in all_paths:
        for command in path:
            if command.command_type != CommandType.ClosePath:
                bounds.min_x = min(command.pos[0], bounds.min_x)
                bounds.max_x = max(command.pos[0], bounds.max_x)
                bounds.min_y = min(command.pos[1], bounds.min_y)
                bounds.max_y = max(command.pos[1], bounds.max_y)

    input_width = bounds.max_x - bounds.min_x
    input_height = bounds.max_y - bounds.min_y
    
    # Offset the points based on the bounds minimums. This makes the points essentially start at (0, 0).
    reset_offset = Vector((-bounds.min_x, -bounds.min_y))
    # Flip the image on the y-axis
    flip_factor = Vector((1.0, -1.0))
    # After flipping, the points need to be offset by the height to bring them back into view.
    flip_offset = Vector((0.0, input_height))

    # Perform base scale and alignment
    for path in all_paths:
        for command in path:
            if command.command_type != CommandType.ClosePath:
                command.translate(reset_offset)
                command.scale(flip_factor)
                command.translate(flip_offset)
    
    # Perform auto-alignment if enabled
    if enable_auto_fit:
        auto_fit(all_paths, input_width, input_height)
    
    # Accumulate path data
    for path in all_paths:
        path_data = []
        for command in path:
            path_data.append(command.to_d())
        
        path_element = ElementTree.Element('path')
        path_element.set('d', ' '.join(path_data))
        svg.append(path_element)

    # Set the view box
    if enable_auto_fit:
        svg.set('viewBox', f'0 0 {target_width}mm {target_height}mm')
    else:
        svg.set('viewBox', f'0 0 {round(input_width, precision)}mm {round(input_height, precision)}mm')
    
    f = open(output_path, 'w')
    f.write(pretty_xml(svg))
    f.close()

def auto_fit(all_paths, input_width, input_height):
    output_width = target_width - x_margin * 2.0
    output_height = target_height - y_margin * 2.0
    
    # Determine the scale needed to reach the target dimensions
    scale_factor = min(output_width / input_width, output_height / input_height)
    
    # The dimensions already factored in 2x the margins, here we just need to move the points over by the margin values.
    margin_offset = Vector((x_margin, y_margin))
    # Aligns the points to the middle
    align_offset = Vector((
        (output_width - input_width * scale_factor) * 0.5, 
        (output_height - input_height * scale_factor) * 0.5
    ))
    
    for path in all_paths:
        for command in path:
            if command.command_type != CommandType.ClosePath:
                command.scale(scale_factor)
                command.translate(margin_offset)
                command.translate(align_offset)

def convert_poly(spline):
    path = []
    
    for i, point in enumerate(spline.points):
        pos = point.co.to_2d()
        
        if i == 0:
            path.append(MoveTo(pos))
        else:
            path.append(LineTo(pos))
    
    if spline.use_cyclic_u:
        path.append(ClosePath())
    
    return path

def convert_bezier(spline):
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
    
    return path


def pretty_xml(elem):
    """Returns a pretty-printed XML string for the Element"""

    rough_string = ElementTree.tostring(elem, 'unicode')
    reparsed = minidom.parseString(rough_string)
    
    return reparsed.toprettyxml(indent='  ')

if __name__ == '__main__':
    main()
