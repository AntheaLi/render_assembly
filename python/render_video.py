from pathlib import Path
import os
import numpy as np
import math

from renderer import PbrtRenderer
from common import create_folder, export_mp4_jpeg, print_info, print_ok
from project_path import root_path
from scipy.spatial.transform import Rotation

import trimesh
import argparse
from assets import *

from PIL import Image
from copy import deepcopy

total_frames = 500
frame_skip = 8
fps = 25

def overlay(args):
    import glob
    from PIL import Image
    output_folder = Path('motions') / 'video' / args.folder
    # all_pngs = glob.glob(output_folder / '*.jpeg')
    all_pngs = os.listdir(output_folder)
    # all_pngs = sorted([x for x in all_pngs if x.endswith('png')])
    all_pngs = sorted([x for x in all_pngs if x.endswith('jpeg')])
    first_frame = all_pngs[0]
    last_frame = all_pngs[-1]
    foreground = Image.open(output_folder / last_frame)
    background = Image.open(output_folder / first_frame)
    alpha_foreground = Image.new("L", foreground.size, 120)
    alpha_background = Image.new("L", background.size, 255)
    foreground.putalpha(alpha_foreground)
    background.putalpha(alpha_background)
    Image.alpha_composite(background, foreground).save(output_folder / 'composite_1.png')
    blended = Image.blend(background, foreground, alpha=0.3)
    blended.putalpha(alpha_background)
    blended.save(output_folder / 'composite_2.png')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ckbd', default=False , action = 'store_true')
    parser.add_argument('--folder', type=str, default='00018')
    parser.add_argument('--extend', default=False, action='store_true')
    parser.add_argument('--overlay', default=False, action='store_true')

    args = parser.parse_args()

    # Create a folder to store the information.
    output_folder = Path('motions') / 'video' / args.folder
    create_folder(output_folder, exist_ok = True)

    # The asset folder.
    asset_root = Path(root_path) / 'asset'
    asset_folder = Path(root_path) / 'asset' / 'motions' / args.folder 
    print(asset_folder)
    obj_asset_folder = Path(root_path) / 'asset' / 'meshes' / args.folder

    all_steps = os.listdir(asset_folder)
    steps, moving_parts = [], []
    for i in range(len(all_steps)):
        data = all_steps[i].split('_')
        steps.append(int(data[0]))
        moving_parts.append(int(data[1]))
    for i in range(len(steps)):
        for j in range(i + 1, len(steps)):
            if steps[i] > steps[j]:
                steps[i], steps[j] = steps[j], steps[i]
                moving_parts[i], moving_parts[j] = moving_parts[j], moving_parts[i]
                all_steps[i], all_steps[j] = all_steps[j], all_steps[i]

    # get first and last frame scene centroid and move all frames by the centroid of the centroids
    obj_paths = []
    for path in os.listdir(obj_asset_folder):
        if path != 'translation.json' and path != 'assembly.obj':
            obj_paths.append(path)
    obj_ids = [int(obj_id_str.split('.')[0]) for obj_id_str in obj_paths]
    obj_ids.sort()
    obj_paths = [str(obj_id) + '.obj' for obj_id in obj_ids]

    min_bbox = []
    max_bbox = []
    initial_transforms = {}
    last_transforms  = {}
    for path in obj_paths:
        obj_idx = int(path.split('.')[0])
        initial_transforms[obj_idx] = np.eye(4)
        last_transforms[obj_idx] = np.eye(4)

    for step_idx in range(len(all_steps)):
        moving_part = moving_parts[step_idx]
        all_frames_int = [int(frame.split('.')[0]) for frame in os.listdir(asset_folder / all_steps[step_idx])]
        all_frames_int.sort()
        all_frames = [str(x) for x in all_frames_int]
        E = np.load(asset_folder / all_steps[step_idx] / '{}.npy'.format(all_frames[-1]))
        last_transforms[moving_part] = E @ initial_transforms[moving_part]

    # load obj meshes
    num_parts = len(obj_paths)
    obj_meshes = {}
    
    meshes, names = load_assembly(obj_asset_folder, return_names=True)

    transformed_mesh_folder = str(obj_asset_folder) + '_transformed'
    os.makedirs(transformed_mesh_folder, exist_ok = True)
    for mesh, name in zip(meshes, names):

        obj_id = int(name.replace('.obj', ''))

        obj_meshes[obj_id] = mesh
        mesh.export(os.path.join(transformed_mesh_folder, name))
        
    # compute scene bounding box for translation and scale
    first_scene = trimesh.Scene()
    last_scene = trimesh.Scene()
    # for cur_obj in num_parts:
    for path in obj_paths:
        obj_idx = int(path.split('.')[0])
        first_mesh = deepcopy(obj_meshes[obj_idx])
        last_mesh = deepcopy(obj_meshes[obj_idx])
        new_vertices = (last_transforms[obj_idx][0:3, 0:3] @ last_mesh.vertices.T).T + last_transforms[obj_idx][0:3, 3]
        last_mesh.vertices = new_vertices
        first_scene.add_geometry(first_mesh)
        last_scene.add_geometry(last_mesh)
        min_bbox_last = np.array(last_mesh.vertices).min(axis=0)
        min_bbox_first = np.array(first_mesh.vertices).min(axis=0)
        max_bbox_last = np.array(last_mesh.vertices).max(axis=0)
        max_bbox_first = np.array(first_mesh.vertices).max(axis=0)
        min_bbox.append(min_bbox_last)
        min_bbox.append(min_bbox_first)
        max_bbox.append(max_bbox_last)
        max_bbox.append(max_bbox_first)

    first_centroid = first_scene.centroid
    last_centroid = last_scene.centroid
    centroid_centroid = first_centroid + last_centroid / 2
    
    min_z = np.array(min_bbox).min(axis=0)[-1]
    bbox = np.array(max_bbox).max(axis=0) - np.array(min_bbox).min(axis=0)
    print('centroid_centroid', centroid_centroid)
    print('bbox', np.linalg.norm(bbox))

    scale = 13 / np.linalg.norm(bbox)
    min_z *= scale
    translation = np.array([-2, 4, 4]) - np.array([0, 0, centroid_centroid[-1]*scale])
    translation = (translation[0], translation[1], translation[2])
    min_z += translation[2]
    print('minz', min_z)
    
    current_transforms = deepcopy(initial_transforms)
    
    object_exists = {}
    for name in names:
        obj_id = int(name.replace('.obj', ''))
        object_exists[obj_id] = True

    overall_frame_cnt = 0
    moving_direction = np.zeros(3)


    for step_idx, step in enumerate(all_steps):
        print_ok('{} / {} steps'.format(step_idx, len(all_steps)))
        moving_part = moving_parts[step_idx]
        all_frames_int = [int(frame.split('.')[0]) for frame in os.listdir(asset_folder / all_steps[step_idx])]
        all_frames_int.sort()
        all_frames = [str(x) for x in all_frames_int]
        
        max_original_frames = int(all_frames[-1])
        if args.extend:
            for j in range(30):
                all_frames.append(str(int(all_frames[-1]) + 1))

        for frame in all_frames:
            idx = int(frame)
            
            out_file_name =  str(output_folder / ('{:04d}.png'.format(overall_frame_cnt)))
            
            overall_frame_cnt += 1

            options = {
                'file_name': out_file_name,
                'light_map':'lightmap.exr',
                'resolution': (720, 720),
                'sample': 128,
                'max_depth': 6,
                'camera_pos': (-7, 20, 15), 
                'camera_lookat' :(0, 0, 1),
                'camera_up': (0, 0, 1),
                
                }

            renderer = PbrtRenderer(options)

            factor = 5.0 #3.5 # 2.5 
            light_intensity = 8.0 # 0.8 
            delta1 = 30
            delta2 = 40
            color_wheel = [np.array([107, 166+delta1, 161+delta1]), np.array([209+delta2, 184+delta1, 148]), np.array([183, 192, 182]), np.array([81, 90, 63]), np.array([220, 203, 182]), np.array([150, 132, 117]), np.array([111, 119, 113])] * 20
            colors = [x/(factor*255) for x in color_wheel]
            
            # Add meshes to the scene.
            if idx <= max_original_frames:
                new_transform = np.load(os.path.join(asset_folder, step, frame + '.npy'))
                moving_direction = new_transform[0:3, 3] - current_transforms[moving_part][0:3, 3]
                current_transforms[moving_part] = new_transform
            else:
                current_transforms[moving_part][0:3, 3] += moving_direction

            for i, path in enumerate(obj_paths):
                obj_idx = int(path.split('.')[0])
                if not object_exists[obj_idx]:
                    continue
                material={
                    'name': 'plastic',
                    'Kd': (colors[i][0], colors[i][1], colors[i][2]),
                    'Ks': (colors[i][0], colors[i][1], colors[i][2]),
                    'roughness': 0.1,
                }

                part_rotation = Rotation.from_matrix(current_transforms[obj_idx][0:3, 0:3]).as_rotvec()
                part_rotation_norm = np.linalg.norm(part_rotation)
                if part_rotation_norm < 1e-5:
                    part_rotation_axis = np.array([1., 0., 0.])
                else:
                    part_rotation_axis = part_rotation / part_rotation_norm
                part_translation = current_transforms[obj_idx][0:3, 3] * scale + translation
                
                renderer.add_tri_mesh(os.path.join(transformed_mesh_folder, path), 
                                        transforms = [('s', scale), 
                                                        ('r', (part_rotation_norm, part_rotation_axis[0], part_rotation_axis[1], part_rotation_axis[2])),
                                                        ('t', (part_translation[0], part_translation[1], part_translation[2]))],
                                        material = material)

            
            if args.ckbd:
                # use checkerboard rendering
                renderer.add_tri_mesh(asset_root / 'mesh/flat_ground.obj',
                texture_img='chkbd_64_0.7',
                transforms=[
                        ('s', 26.),
                        ('t', (0, 0, min_z))
                    ])
            else:
                renderer.add_tri_mesh(asset_root / 'mesh/flat_ground.obj',
                texture_img='grid.png',
                transforms=[
                        ('s', 26.),
                        ('t', (0., 0, -10.))
                    ])

            # render
            renderer.render(light_magnitude=light_intensity)

            print_info('{:d}/{:d} done...'.format(idx, len(all_frames)))

        object_exists[moving_part] = False

        export_mp4_jpeg(output_folder, output_folder / 'demo.mp4', fps=fps)
        
    

