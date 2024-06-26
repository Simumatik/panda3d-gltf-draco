import traceback
import sys
import os
import math
from direct.showbase.ShowBase import ShowBase
from direct.task import Task

# from panda3d.core import
# from panda3d.core import AmbientLight, DirectionalLight
import panda3d.core as p3d
import simplepbr

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
        main_node = self.render.attachNewNode(f"main")

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
                model.reparent_to(main_node)
                biggestRadius = max( biggestRadius, model.getBounds().getRadius() )
                self.models.append(model)
        except Exception as e:
            print("EXCEPTION", e)

        
        if "--no-translation" not in options:
            startx = 0
            step = 1
            print("biggest radius", biggestRadius)
            for model in self.models:
                model.setPos(startx, 0, 0)
                print ( model.getBounds() )
                startx = startx + biggestRadius + step

        #self.model_root = self.loader.load_model(infile, noCache=True)

        self.accept("escape", sys.exit)
        self.accept("q", sys.exit)
        self.accept("w", self.toggle_wireframe)
        self.accept("t", self.toggle_texture)
        self.accept("n", self.toggle_normal_maps)
        self.accept("e", self.toggle_emission_maps)
        self.accept("o", self.toggle_occlusion_maps)
        self.accept("a", self.toggle_ambient_light)
        self.accept("p", self.print_camera_pos)
        #self.accept("shift-l", self.model_root.ls)
        #self.accept("shift-a", self.model_root.analyze)

        #self.model_root.reparent_to(self.render)

        # bounds = self.model_root.getBounds()
        # center = bounds.get_center()
        # if bounds.is_empty():
        #     radius = 1
        # else:
        #     radius = bounds.get_radius()

        radius = 1

        fov = self.camLens.get_fov()
        distance = radius / math.tan(math.radians(min(fov[0], fov[1]) / 2.0))
        self.camLens.set_near(min(self.camLens.get_default_near(), radius / 2))
        self.camLens.set_far(max(self.camLens.get_default_far(), distance + radius * 2))
        #trackball = self.trackball.node()
        #trackball.set_origin(center)
        #trackball.set_pos(0, distance, 0)
        #trackball.setForwardScale(distance * 0.006)




        # # Create a light if the model does not have one
        if not main_node.find("**/+Light"):
            self.light = self.render.attach_new_node(p3d.PointLight("light"))
            self.light.set_pos(0, -distance, distance)
            self.render.set_light(self.light)

        # Move lights to render
        main_node.clear_light()
        for light in main_node.find_all_matches("**/+Light"):
            light.parent.wrt_reparent_to(self.render)
            self.render.set_light(light)

        # Add some ambient light
        self.ambient = self.render.attach_new_node(p3d.AmbientLight("ambient"))
        self.ambient.node().set_color((0.2, 0.2, 0.2, 1))
        self.render.set_light(self.ambient)

        # if self.model_root.find("**/+Character"):
        #     self.anims = p3d.AnimControlCollection()
        #     p3d.autoBind(self.model_root.node(), self.anims, ~0)
        #     if self.anims.get_num_anims() > 0:
        #         self.anims.get_anim(0).loop(True)
            
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


def main():
    App().run()


if __name__ == "__main__":
    main()

# if __name__ == "__main__":
#     print("loading")

#     _world = ShowBase(fStartDirect=True)
#     _world.accept("escape", sys.exit)

#     _world.camera.setPos(0.1, 0.1, 0.1)
#     # _world.camera.setPos(0.2,0.4,0.2)
#     _world.camera.lookAt(0, 0, 0)
#     _world.camLens.setNear(0.01)
#     # _world.disableMouse()
#     _world.setFrameRateMeter(True)

#     alight = AmbientLight("alight")
#     alight.setColor((1, 1, 1, 1))
#     alnp = _world.render.attachNewNode(alight)
#     _world.render.setLight(alnp)

#     dlight = DirectionalLight("dlight")
#     dlight.setColor((0.3, 0.3, 0.3, 1))
#     dlnp = _world.render.attachNewNode(dlight)
#     _world.render.setLight(dlnp)

#     main_node = _world.render.attachNewNode(f"main")

#     filename = Filename.fromOsSpecific("duck.glb")
#     if len(sys.argv) > 1 and sys.argv[1].endswith("glb"):
#         filename = Filename.fromOsSpecific(sys.argv[1])

#     try:
#         print("loading glb")

#         # load_model(filename)
#         model = _world.loader.loadModel(filename)
#         print("done")
#         model.setPos(0, 0, 0)
#         model.reparentTo(main_node)
#         _world.run()
#     except RuntimeError:
#         traceback.print_exc()

#     print("exit")
