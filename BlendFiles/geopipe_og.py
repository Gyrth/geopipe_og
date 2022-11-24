import bpy
import bmesh
import math
from mathutils import *
import os.path
from os import walk
import re
import xml.etree.ElementTree as ET
import lxml.etree as etree
from xml.etree.ElementTree import XMLParser
from pathlib import Path
from math import radians
from bpy.props import BoolProperty, IntVectorProperty, StringProperty
from bpy.types import (Panel, Operator)
import random
from xml.etree import ElementTree
from xml.dom import minidom
from shutil import copyfile
from os import listdir
from os.path import isfile, join
from PIL import Image, ImageDraw, ImageFilter
from math import pi
from mathutils import Color

bpy.types.Scene.project_name = StringProperty(subtype='FILE_NAME', name="Project Name")

export_limit = -1

cached_object_names = []
cached_object_meshes = []

plant_names = [ "Image_49",
                "Image_50" ]

cutout_names = [ "Image_42" ]

double_sided_names = []

def ExportModels(project_name):
    objects = bpy.context.scene.objects
    for obj in objects:
        obj.select_set(True)
    
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    for obj in objects:
        obj.select_set(False)
    
    # Then set the origin to the center of the bounding box, just like OG does in-engine.

    resolved_export_path = bpy.path.abspath("//../Data/Models/")
    print("--------------------------------------")
    print("Model Export path : ", resolved_export_path)
    print("--------------------------------------")
    
    # Make sure the export folder exists before writing to it.
    obj_export_path = resolved_export_path + project_name + "/"
    if not os.path.exists(obj_export_path):
        os.makedirs(obj_export_path)
    
    # Deselect everything.
    for obj in objects:
        obj.select_set(False)
    
    exported_model_names = []
    
    for obj in objects:
        # Do not export any object that isn't a mesh, for example Empty, Light and Camera.
        if obj.type != 'MESH' : continue
        # Select the object so that we can export ONLY this mesh in a separate file.
        obj.select_set(True)
        # Check if the name of the mesh has already been exported.
        model_name = obj.data.name
        model_name = model_name.replace(".", "")
        # Skip the export if this mesh is already written to the disk.
        if not model_name in exported_model_names:
            old_quat = obj.rotation_quaternion.copy()
            old_scale = obj.scale.copy()
            obj.rotation_quaternion.x = 0.0
            obj.rotation_quaternion.y = 0.0
            obj.rotation_quaternion.z = 0.0
            obj.rotation_quaternion.w = 1.0
            obj.scale.x = 1.0
            obj.scale.y = 1.0
            obj.scale.z = 1.0
            exported_model_names.append(model_name)
            # Export using the selected object and don't write any materials. This is done later in XML.
            bpy.ops.export_scene.obj(filepath=obj_export_path + model_name + ".obj", use_selection=True, use_materials=False, axis_forward="-Z", axis_up="Y")
            obj.rotation_quaternion = old_quat
            obj.scale = old_scale
        
        # Deselect the exported mesh so that the next mesh can be selected.
        obj.select_set(False)
        
        # For debug purposes, only export export_limit meshes.
        if len(exported_model_names) == export_limit:
            break
    
    # Display the amount of exported meshes for statistics.
    print("Exported " + str(len(exported_model_names)) + " Models.")

def ExportTextures(project_name):
    objects = bpy.context.scene.objects
    for obj in objects:
        obj.select_set(False)
    
    resolved_export_path = bpy.path.abspath("//../Data/Textures/")
    print("--------------------------------------")
    print("Texture Export path : ", resolved_export_path)
    print("--------------------------------------")
    
    # Make sure the export folder exists before writing to it.
    texture_export_path = resolved_export_path + project_name + "/"
    if not os.path.exists(texture_export_path):
        os.makedirs(texture_export_path)
    
    exported_texture_names = []
    
    for obj in objects:
        if obj.type != 'MESH' : continue
        
        for material in obj.data.materials:
            model_name = obj.data.name
            material.use_nodes = True
            base_color = None
            diffuse = None
            specular_glossiness = None
            image_name = None
            
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE":
#                    print(node.label)
                    if node.label == "BASE COLOR":
                        base_color = node.image
                        image_name = node.image.name
                    elif node.label == "DIFFUSE":
                        diffuse = node.image
                        image_name = node.image.name
                    elif node.label == "SPECULAR GLOSSINESS":
                        specular_glossiness = node.image
                        image_name = node.image.name
            
            if base_color != None:
                image_name = base_color.name
                image_name = image_name.replace(".", "")
                if not image_name in exported_texture_names:
                    
                    image_edited = base_color.copy()
                    image_edited.update()
                    
                    width = image_edited.size[0]
                    height = image_edited.size[1]
                    pixels = list(image_edited.pixels)
                    
                    # Set the opacity of the texture to 1% so that the material has no reflection in-game.
                    if any(plant_name in image_name for plant_name in plant_names):
                        pass
                    elif any(coutout_name in image_name for coutout_name in coutout_names):
                        pass
                    else:
                        for i in range(3, len(pixels), 4):
                            pixels[i] = 0.01
                    
                    image_edited.pixels[:] = pixels
                    image_edited.update()
                    
                    next_width = math.pow(2, math.ceil(math.log(width)/math.log(2)))
                    next_height = math.pow(2, math.ceil(math.log(height)/math.log(2)))
                    image_edited.scale(int(next_width), int(next_height))
                    
                    image_edited.save_render(texture_export_path + image_name + ".png")
                    exported_texture_names.append(image_name)
                    bpy.data.images.remove(image_edited)
            elif diffuse != None and specular_glossiness != None:
                diffuse_image_name = diffuse.name
                diffuse_image_name = diffuse_image_name.replace(".", "")
                if not diffuse_image_name in exported_texture_names:
                    diffuse_image_edited = diffuse.copy()
                    diffuse_image_edited.update()
                    
                    width = diffuse_image_edited.size[0]
                    height = diffuse_image_edited.size[1]
                    diffuse_pixels = list(diffuse_image_edited.pixels)
                    specular_glosinness_pixels = list(specular_glossiness.pixels)
                    
                    for i in range(3, len(diffuse_pixels), 4):
                        diffuse_pixels[i] = 0.01 if specular_glosinness_pixels[i] < 0.5 else 0.5
                    
                    diffuse_image_edited.pixels[:] = diffuse_pixels
                    diffuse_image_edited.update()
                    
                    next_width = math.pow(2, math.ceil(math.log(width)/math.log(2)))
                    next_height = math.pow(2, math.ceil(math.log(height)/math.log(2)))
                    max_next = int(max(next_width, next_height))
                    diffuse_image_edited.scale(max_next, max_next)
                    
                    diffuse_image_edited.save_render(texture_export_path + diffuse_image_name + ".png")
                    print(diffuse_image_name)
                    exported_texture_names.append(diffuse_image_name)
                    bpy.data.images.remove(diffuse_image_edited)
            elif diffuse != None:
                diffuse_image_name = diffuse.name
                diffuse_image_name = diffuse_image_name.replace(".", "")
                if not diffuse_image_name in exported_texture_names:
                    diffuse_image_edited = diffuse.copy()
                    diffuse_image_edited.update()
                    
                    width = diffuse_image_edited.size[0]
                    height = diffuse_image_edited.size[1]
                    diffuse_pixels = list(diffuse_image_edited.pixels)
                    
                    for i in range(3, len(diffuse_pixels), 4):
                        diffuse_pixels[i] = 0.01
                    
                    diffuse_image_edited.pixels[:] = diffuse_pixels
                    diffuse_image_edited.update()
                    
                    next_width = math.pow(2, math.ceil(math.log(width)/math.log(2)))
                    next_height = math.pow(2, math.ceil(math.log(height)/math.log(2)))
                    max_next = int(max(next_width, next_height))
                    diffuse_image_edited.scale(max_next, max_next)
                    
                    diffuse_image_edited.save_render(texture_export_path + diffuse_image_name + ".png")
                    print(diffuse_image_name)
                    exported_texture_names.append(diffuse_image_name)
                    bpy.data.images.remove(diffuse_image_edited)
            
#            if len(exported_texture_names) == export_limit:
#                break
#        
#        if len(exported_texture_names) == export_limit:
#            break
    
    # Display the amount of exported textures for statistics.
    print("Exported " + str(len(exported_texture_names)) + " Textures.")

def ExportXML(project_name):
    objects = bpy.context.scene.objects
    for obj in objects:
        obj.select_set(False)
    
    resolved_export_path = bpy.path.abspath("//../Data/Objects/")
    print("--------------------------------------")
    print("XML Export path : ", resolved_export_path)
    print("--------------------------------------")
    
    # Make sure the export folder exists before writing to it.
    xml_export_path = resolved_export_path + project_name + "/"
    if not os.path.exists(xml_export_path):
        os.makedirs(xml_export_path)
    
    exported_xml_names = []
    
    for obj in objects:
        if obj.type != 'MESH' : continue
    
        model_name = obj.data.name
        model_name = model_name.replace(".", "")
        texture_name = ""
        
        if model_name in exported_xml_names : continue
    
        for material in obj.data.materials:
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE":
                    if node.label == "BASE COLOR":
                        texture_name = node.image.name
                    elif node.label == "DIFFUSE":
                        texture_name = node.image.name
        
        texture_name = texture_name.replace(".", "")
        
        object_xml_root = minidom.Document()
        object_xml = object_xml_root.createElement('Object')
        object_xml_root.appendChild(object_xml)
        
        # First the model path.
        model_xml = object_xml_root.createElement('Model')
        model_path = object_xml_root.createTextNode("Data/Models/" + project_name + "/" + model_name + ".obj")
        model_xml.appendChild(model_path)
        object_xml.appendChild(model_xml)
        
        # Then the colormap.
        colormap_xml = object_xml_root.createElement('ColorMap')
        if texture_name == "":
            colormap_path = object_xml_root.createTextNode("Data/Textures/black.png")
        else:
            colormap_path = object_xml_root.createTextNode("Data/Textures/" + project_name + "/" + texture_name + ".png")
        colormap_xml.appendChild(colormap_path)
        object_xml.appendChild(colormap_xml)
        
        # The normalmap is all the same.
        normalmap_xml = object_xml_root.createElement('NormalMap')
        normalmap_path = object_xml_root.createTextNode("Data/Textures/normal.tga")
        normalmap_xml.appendChild(normalmap_path)
        object_xml.appendChild(normalmap_xml)
        
        # The shadername is also the same.
        shadername_xml = object_xml_root.createElement('ShaderName')
        if any(plant_name in texture_name for plant_name in plant_names):
            
#            translucency_xml = object_xml_root.createElement('TranslucencyMap')
#            translucency_path = object_xml_root.createTextNode("Data/Textures/Plants/Trees/temperate/green_bush_t.tga")
#            translucency_xml.appendChild(translucency_path)
#            object_xml.appendChild(translucency_xml)
            
            wind_xml = object_xml_root.createElement('WindMap')
            wind_path = object_xml_root.createTextNode("Data/Textures/default_windmap.png")
            wind_xml.appendChild(wind_path)
            object_xml.appendChild(wind_xml)
            
            shadername_path = object_xml_root.createTextNode("envobject #TANGENT #ALPHA #PLANT #NO_DECALS")
            
            # Add an extra tag for doublesided.
            flags_xml = object_xml_root.createElement('flags')
            # Plants are double sided, have no collision and create leaf particles.
            flags_xml.setAttribute('no_collision', 'true')
            flags_xml.setAttribute('bush_collision', 'true')
            flags_xml.setAttribute('double_sided', 'true')
            object_xml.appendChild(flags_xml)
        elif any(cutout_name in texture_name for cutout_name in cutout_names):
            shadername_path = object_xml_root.createTextNode("envobject #ALPHA #PLANT")
            
            # Add an extra tag for doublesided.
            flags_xml = object_xml_root.createElement('flags')
            flags_xml.setAttribute('double_sided', 'true')
            object_xml.appendChild(flags_xml)
        else:
            shadername_path = object_xml_root.createTextNode("envobject #TANGENT")
            # An extra check to see if this object is double sided.
            if any(double_sided_name in model_name for double_sided_name in double_sided_names):
                flags_xml = object_xml_root.createElement('flags')
                flags_xml.setAttribute('double_sided', 'true')
                object_xml.appendChild(flags_xml)
            
        shadername_xml.appendChild(shadername_path)
        object_xml.appendChild(shadername_xml)
          
        xml_str = object_xml_root.toprettyxml(indent ="\t")
        
        # Export the XML.
        xml_export_path = resolved_export_path + project_name + "/"
        if not os.path.exists(xml_export_path):
            os.makedirs(xml_export_path)
        
        with open(xml_export_path + model_name + ".xml", "w", encoding="utf8") as outfile:
            outfile.write(xml_str)
        
        exported_xml_names.append(model_name)
        if len(exported_xml_names) == export_limit:
            break
    
    # Display the amount of exported textures for statistics.
    print("Exported " + str(len(exported_xml_names)) + " XML.")

def ExportLevelXML(project_name):
    objects = bpy.context.scene.objects
    for obj in objects:
        obj.select_set(False)
    
    resolved_export_path = bpy.path.abspath("//../Data/Levels/")
    print("--------------------------------------")
    print("Level XML Export path : ", resolved_export_path)
    print("--------------------------------------")
    
    # Make sure the export folder exists before writing to it.
    xml_export_path = resolved_export_path + project_name + "/"
    if not os.path.exists(xml_export_path):
        os.makedirs(xml_export_path)

    level_xml_root = minidom.Document()
    actor_objects_xml = level_xml_root.createElement('ActorObjects')
    level_xml_root.appendChild(actor_objects_xml)
    known_exported_names = []
    object_counter = 0
    
    for obj in objects:
        if obj.type != 'MESH' : continue
    
        model_name = obj.data.name
        model_name = model_name.replace(".", "")
        
        local_bbox_center = 0.125 * sum((Vector(b) for b in obj.bound_box), Vector())
        global_bbox_center = obj.matrix_world @ local_bbox_center
        
        object_xml = level_xml_root.createElement('EnvObject')
        object_xml.setAttribute('t0', str(global_bbox_center.x))
        object_xml.setAttribute('t1', str(global_bbox_center.z))
        object_xml.setAttribute('t2', str(global_bbox_center.y * -1.0))

        object_xml.setAttribute('s0', str(obj.scale.x))
        object_xml.setAttribute('s1', str(obj.scale.z))
        object_xml.setAttribute('s2', str(obj.scale.y))
        
        obj.rotation_mode = "QUATERNION"
        object_xml.setAttribute('q0', str(obj.rotation_quaternion.x))
        object_xml.setAttribute('q1', str(obj.rotation_quaternion.z))
        object_xml.setAttribute('q2', str(obj.rotation_quaternion.y * -1.0))
        object_xml.setAttribute('q3', str(obj.rotation_quaternion.w))
        
        object_xml.setAttribute('type_file', "Data/Objects/" + project_name + "/" + model_name + ".xml")
        actor_objects_xml.appendChild(object_xml)
        object_counter += 1
        
        if not model_name in known_exported_names:
            known_exported_names.append(model_name)
        
        if len(known_exported_names) == export_limit:
            break
          
    xml_str = level_xml_root.toprettyxml(indent ="\t")
    
    level_data = ""
    with open(resolved_export_path + "default_level_data.xml", 'r') as file:
        level_data = file.read()
    
    split_xml = xml_str.split("\n")
    split_xml.insert(1, level_data)
    xml_str = "\n".join(split_xml)
    
    # Export the XML.
    xml_export_path = resolved_export_path + project_name + "/"
    if not os.path.exists(xml_export_path):
        os.makedirs(xml_export_path)
    
    with open(xml_export_path + project_name + ".xml", "w", encoding="utf8") as outfile:
        outfile.write(xml_str)
    
    print("Exported " + str(object_counter) + " objects to " + project_name + ".xml")

class ExportModelsOperator(Operator):
    bl_label = "Operator"
    bl_idname = "object.export_models"
    
    def execute(self, context):
        ExportModels(context.scene.project_name)
        return {'FINISHED'}

class ExportTexturesOperator(Operator):
    bl_label = "Operator"
    bl_idname = "object.export_textures"
    
    def execute(self, context):
        ExportTextures(context.scene.project_name)
        return {'FINISHED'}

class ExportXMLOperator(Operator):
    bl_label = "Operator"
    bl_idname = "object.export_xml"
    
    def execute(self, context):
        ExportXML(context.scene.project_name)
        return {'FINISHED'}

class ExportLevelXMLOperator(Operator):
    bl_label = "Operator"
    bl_idname = "object.export_level_xml"
    
    def execute(self, context):
        ExportLevelXML(context.scene.project_name)
        return {'FINISHED'}

class GEOPIPEOGEXPORT_PT_Panel(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Geopipe Overgrowth Export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'

    def draw(self, context):
        self.layout.prop(context.scene, "project_name")
        self.layout.operator(ExportModelsOperator.bl_idname, text="Export Models", icon="LIBRARY_DATA_DIRECT")
        self.layout.operator(ExportTexturesOperator.bl_idname, text="Export Textures", icon="LIBRARY_DATA_DIRECT")
        self.layout.operator(ExportXMLOperator.bl_idname, text="Export XML", icon="LIBRARY_DATA_DIRECT")
        self.layout.operator(ExportLevelXMLOperator.bl_idname, text="Export Level XML", icon="LIBRARY_DATA_DIRECT")

def register():
    bpy.utils.register_class(GEOPIPEOGEXPORT_PT_Panel)
    bpy.utils.register_class(ExportModelsOperator)
    bpy.utils.register_class(ExportTexturesOperator)
    bpy.utils.register_class(ExportXMLOperator)
    bpy.utils.register_class(ExportLevelXMLOperator)

def unregister():
    bpy.utils.unregister_class(GEOPIPEOGEXPORT_PT_Panel)
    bpy.utils.unregister_class(ExportModelsOperator)
    bpy.utils.unregister_class(ExportTexturesOperator)
    bpy.utils.unregister_class(ExportXMLOperator)
    bpy.utils.unregister_class(ExportLevelXMLOperator)

if __name__ == "__main__":
    register()
else:
    print('starting addon')
    register()