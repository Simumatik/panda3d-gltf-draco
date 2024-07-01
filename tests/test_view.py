import sys
import os
import math
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText

import panda3d.core as p3d
import simplepbr

from panda3d.core import (LVector3, LMatrix4, LineSegs)

p3d.load_prc_file_data(
    "",
    "window-size 1024 768\n"
    "texture-minfilter mipmap\n"
    "texture-anisotropic-degree 16\n",
)

class App(ShowBase):
    def __init__(self):
        if len(sys.argv) < 2:
            print("Missing input file")
            sys.exit(1)

        super().__init__()

        # Initial setup
        self.pipeline = simplepbr.init()

        ## Setup collision handling
        self.traverser = self.cTrav = p3d.CollisionTraverser('collision_traverser')
        self.picker_collision_handler = p3d.CollisionHandlerQueue()
        self.picker = p3d.CollisionNode('mouser_ray')
        self.picker_node = self.camera.attach_new_node(self.picker)
        self.picker.set_from_collide_mask(p3d.GeomNode.get_default_collide_mask())
        
        self.picker_ray = p3d.CollisionRay()
        self.picker.add_solid( self.picker_ray )
        self.traverser.add_collider(self.picker_node, self.picker_collision_handler)

        self.models = []
        self.main_node = self.render.attach_new_node(f"main")

        self.origin_axis = self.create_axis_lines()
        self.origin_node = p3d.NodePath( self.origin_axis )

        self.selected_model = None
        self.selection_axis = self.create_axis_lines("selection_axis")
        self.selection_axis_node = p3d.NodePath( self.selection_axis )

        self.selected_model_text = OnscreenText(text='', pos=(0, 0), scale=0.07)
        self.selected_model_text.setAlign(p3d.TextNode.ALeft)
        self.selected_model_text.setTextPos(-1.28, 0.93)
        
        # Process script arguments
        arguments = sys.argv[1:]
        options = []
        files = []
        while len(arguments) > 0:
            arg = arguments.pop(0)
            if arg.startswith("-") or arg.startswith("--"):
                options.append(arg)
            else:
                files.append(arg)

        # Load any model files from script arguments
        while files: 
            file = files.pop(0)
            infile = p3d.Filename.from_os_specific(os.path.abspath(file))
            p3d.get_model_path().prepend_directory(infile.get_dirname())
            model = self.loader.load_model(infile, noCache=True)
            model.set_name( f"model-{infile.get_basename_wo_extension()}")
            model.set_tag("pickable", 'true')
            model.reparent_to(self.main_node)
            self.models.append(model)

        # If multiple models was loaded, display them side by side (unless --no-translation was specified)
        if "--no-translation" not in options:
            startx = 0
            for model in self.models:
                model.setPos(startx, 0, 0)
                startx = startx + model.get_bounds().get_radius() * 2

        self.accept("escape", sys.exit)
        self.accept("q", sys.exit)
        self.accept("w", self.toggle_wireframe)
        self.accept("t", self.toggle_texture)
        self.accept("n", self.toggle_normal_maps)
        self.accept("e", self.toggle_emission_maps)
        self.accept("o", self.toggle_occlusion_maps)
        self.accept("a", self.toggle_ambient_light)
        self.accept("d", self.toggle_display_origin)
        self.accept("tab", self.select_next_object)
        self.accept("p", self.print_camera_pos)
        self.accept("mouse1", self.pick_object)

        # Setup camera to fit the main node bounds withing its field of view
        bounds = self.main_node.get_bounds()
        center = bounds.get_center()
        if bounds.is_empty():
            radius = 1
        else:
            radius = bounds.get_radius()

        fov = self.camLens.get_fov()
        distance = radius / math.tan(math.radians(min(fov[0], fov[1]) / 2.0))
        self.camLens.set_near(min(self.camLens.get_default_near(), radius / 2))
        self.camLens.set_far(max(self.camLens.get_default_far(), distance + radius * 2))

        camera_position = LVector3(0, -distance * 2, 0)

        # # Create a light if the model does not have one
        if not self.main_node.find("**/+Light"):
            self.light = self.render.attach_new_node(p3d.PointLight("light"))
            self.light.set_pos(0, -distance, distance)
            self.render.set_light(self.light)

        # Move lights to render
        self.main_node.clear_light()
        for light in self.main_node.find_all_matches("**/+Light"):
            light.parent.wrt_reparent_to(self.render)
            self.render.set_light(light)

        # Add some ambient light
        self.ambient = self.render.attach_new_node(p3d.AmbientLight("ambient"))
        self.ambient.node().set_color((0.2, 0.2, 0.2, 1))
        self.render.set_light(self.ambient)

        self.set_camera_position(camera_position, look_at=center)
   
    def toggle_normal_maps(self):
        self.pipeline.use_normal_maps = not self.pipeline.use_normal_maps

    def toggle_emission_maps(self):
        self.pipeline.use_emission_maps = not self.pipeline.use_emission_maps

    def toggle_occlusion_maps(self):
        self.pipeline.use_occlusion_maps = not self.pipeline.use_occlusion_maps

    def toggle_ambient_light(self):
        if self.render.has_light(self.ambient):
            self.render.clear_light(self.ambient)
        else:
            self.render.set_light(self.ambient)

    def toggle_display_origin(self):       
        if self.origin_node.is_singleton():
            self.origin_node.reparent_to(self.render)
        else:
            self.origin_node.detach_node()

    def print_camera_pos(self):
        print( self.camera.getPos() )

    def create_axis_lines(self, name="origin", length=0.75, thickness=2.0):
        lines = LineSegs(name)
        lines.set_thickness(thickness)
        # Draw X-axis
        lines.set_color(1, 0, 0, 1) # red
        lines.move_to(0, 0, 0)
        lines.draw_to(length, 0, 0)
        # Draw Y-axis
        lines.set_color(0, 1, 0, 1) # green
        lines.move_to(0, 0, 0)
        lines.draw_to(0, length, 0)
        # Draw Z-axis
        lines.set_color(0, 0, 1, 1) # blue
        lines.move_to(0, 0, 0)
        lines.draw_to(0, 0, length)
        return lines.create()

    def select_object_node(self, node):
        if node is None or node not in self.models:
            # Deselect if the user clicked something other than the models
            self.selected_model = None
            self.selection_axis_node.detach_node()
            self.selected_model_text.setText("")
            return
        
        # Attach the axis node to the next model
        self.selected_model = node
        self.selection_axis_node.reparent_to(self.selected_model)
        self.selected_model_text.setText(self.selected_model.name)

    def select_next_object(self):
        # Skip if no models
        if not len ( self.models ):
            return

        # Get the first model if none is selected
        if self.selected_model is None:
            next_index = 0
        else:
            next_index = self.models.index(self.selected_model) + 1

        if next_index == len( self.models ):
            self.select_object_node(None)
        else: 
            self.select_object_node(self.models[ next_index ])

    def pick_object(self):
        if not self.mouseWatcherNode.has_mouse():
            return
        
        mpos = self.mouseWatcherNode.getMouse()
        self.picker_ray.set_from_lens(self.camNode, mpos.getX(), mpos.getY())
        self.traverser.traverse(self.render)

        # Assume for simplicity's sake that myHandler is a CollisionHandlerQueue.
        if not self.picker_collision_handler.get_num_entries():
            self.select_object_node(None)
            return
        
        # This is so we get the closest object
        self.picker_collision_handler.sort_entries()
        picked_object = self.picker_collision_handler.get_entry(0).get_into_node_path()
        picked_object = picked_object.find_net_tag('pickable')
        
        if not picked_object.is_empty():
            self.select_object_node(picked_object)

    def set_camera_position(self, position: LVector3 = LVector3(10, 0, 5), look_at: LVector3 = LVector3(0,0,0)):
        # Disable mouse to stop it from resetting the camera matrix
        self.disable_mouse()
        
        # Set the camera position and look-at vectors
        self.camera.set_pos(position)
        self.camera.look_at(look_at)
       
        # Copy the camera matrix
        mat = LMatrix4(self.camera.get_mat())
        mat.invert_in_place()

        # Update the mouse transform
        self.mouseInterfaceNode.set_mat(mat)
        self.enable_mouse()

def main():
    try:
        App().run()
    except AssertionError as e:
        print("madderfacking assertion error", e)
        import traceback
        traceback.print_exception(e)


if __name__ == "__main__":
    main()