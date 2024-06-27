import sys
import os
import math
from direct.showbase.ShowBase import ShowBase

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

        self.pipeline = simplepbr.init()
        self.models = []
        self.main_node = self.render.attachNewNode(f"main")

        origin_axis = self.create_unit_axis_node()
        self.origin = self.render.attachNewNode( origin_axis )
         

        arguments = sys.argv[1:]

        options = []
        files = []
        while len(arguments) > 0:
            arg = arguments.pop(0)
            if arg.startswith("-") or arg.startswith("--"):
                options.append(arg)
            else:
                files.append(arg)

        try:
            biggestRadius = 0.01
            while files: 
                file = files.pop(0)
                print(file)
                infile = p3d.Filename.from_os_specific(os.path.abspath(file))
                print("infile: ", infile)
                p3d.get_model_path().prepend_directory(infile.get_dirname())
                model = self.loader.load_model(infile, noCache=True)
                model.reparent_to(self.main_node)
                biggestRadius = max( biggestRadius, model.getBounds().getRadius() )
                self.models.append(model)
        except Exception as e:
            print("EXCEPTION", e)

        
        if "--no-translation" not in options:
            startx = 0
            #step = 1
            for model in self.models:
                model.setPos(startx, 0, 0)
                startx = startx + model.getBounds().getRadius() * 2
                #startx = startx + biggestRadius + step

        self.accept("escape", sys.exit)
        self.accept("q", sys.exit)
        self.accept("w", self.toggle_wireframe)
        self.accept("t", self.toggle_texture)
        self.accept("n", self.toggle_normal_maps)
        self.accept("e", self.toggle_emission_maps)
        self.accept("o", self.toggle_occlusion_maps)
        self.accept("a", self.toggle_ambient_light)
        self.accept("p", self.print_camera_pos)

        bounds = self.main_node.getBounds()
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

        self.set_camera_position(camera_position, lookAt=center)
   
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

    def print_camera_pos(self):
        print( self.camera.getPos() )

    def create_unit_axis_node(self, name="origin", length=1.0, thickness=5.0):
        lines = LineSegs(name)
        lines.setColor(1, 0, 0, 1)
        lines.setThickness(thickness)
        lines.moveTo(0, 0, 0)      
        lines.drawTo(0, 0, length)
        lines.setColor(0,1,0,1)
        lines.moveTo(0,0,0)      
        lines.drawTo(0, length, 0)
        lines.setColor(0,0,1,1)
        lines.moveTo(0,0,0)      
        lines.drawTo(length,0,0)
        return lines.create()

    def set_camera_position(self, position: LVector3 = LVector3(10, 0, 5), lookAt: LVector3 = LVector3(0,0,0)):
        self.disableMouse()
        
        self.camera.setPos(position)
        self.camera.lookAt(lookAt)
       
        # Copy the camera matrix
        mat = LMatrix4(self.camera.getMat())
        mat.invertInPlace()

        # Update the mouse transform
        self.mouseInterfaceNode.setMat(mat)
        self.enableMouse()

def main():
    try:
        App().run()
    except AssertionError as e:
        print("madderfacking assertion error", e)
        import traceback
        traceback.print_exception(e)


if __name__ == "__main__":
    main()