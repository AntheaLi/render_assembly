from pathlib import Path
import os
import numpy as np
import math

from renderer import PbrtRenderer
from common import create_folder, export_mp4_jpeg, print_info
from project_path import root_path
from scipy.spatial.transform import Rotation

import trimesh
import argparse

from PIL import Image

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
    parser.add_argument('--single-frame', action = 'store_true')
    parser.add_argument('--export-video', action = 'store_true')
    parser.add_argument('--overlay', action = 'store_true')
    parser.add_argument('--no-bg', default=False , action = 'store_true')
    parser.add_argument('--no-video', default=False , action = 'store_true')
    parser.add_argument('--ckbd', default=False , action = 'store_true')
    parser.add_argument('--folder', type=str, default='00002')
    parser.add_argument('--frame', type = int, default = 0)

    args = parser.parse_args()

    if args.single_frame:
        frame = args.frame

        # Create a folder to store the information.
        output_folder = Path('motions') / args.folder
        create_folder(output_folder, exist_ok = True)

        # The asset folder.
        asset_root = Path(root_path) / 'asset'
        asset_folder = Path(root_path) / 'asset' / 'motions' / args.folder / str(frame)

        # Create the render.
        scale = 0.1
        options = {
            # 'file_name': str(output_folder / (str(frame) + '.png')),
            'file_name': str(output_folder / (str(args.folder) + '.png')),
            # 'light_map': 'uffizi-large.exr',
            'light_map':'lightmap.exr',
            # 'resolution': (1200, 1200),
            'resolution': (900, 900),
            # 'resolution': (600, 600),
            # 'sample': 16,
            'sample': 512,
            # 'max_depth': 4,
            'max_depth': 6,
            # 'camera_pos': (12.5, -12, 12.1), # uffizi
            'camera_pos': (-12+5, 20-5, 12), # lightmap
            # 'camera_pos': (10, 10, 12.1),
            # 'camera_lookat': (0.3+0.1, 0, -0.4+0.1),
            'camera_lookat' :(0, 0, 0),
            # 'camera_lookat': (0.15, 0, -0.2),
            'camera_up': (0, 0, 1),
        }

        renderer = PbrtRenderer(options)

        part_list = os.listdir(asset_folder)
        print('num part', len(part_list))
        factor = 5.0 # 3.0
        light_intensity = 8.0 #0.8 #3.0
        color_wheel = [np.array([107, 166, 161]), np.array([209, 184, 148]), np.array([183, 192, 182]), np.array([81, 90, 63]), np.array([220, 203, 182]), np.array([150, 132, 117]), np.array([111, 119, 113])] * 20
        colors = [x/(factor*255) for x in color_wheel]
        # Add meshes to the scene.
        obj_id = 0
        scene = trimesh.Scene()
        for obj_idx in range(len(part_list)):
            # path_to_mesh = asset_folder / str(frame) / (str(obj_id) + '.obj')
            path_to_mesh = asset_folder / (str(obj_idx) + '.obj')
            print(path_to_mesh)
            mesh = trimesh.load(path_to_mesh)
            scene.add_geometry(mesh)
        centroid_centroid = scene.centroid
        print(centroid_centroid)
        # translation = np.array([2, -2, 4]) - np.array([0, 0, centroid_centroid[-1]]) 
        translation = np.array([-2, 4, 4]) #- np.array([0, 0, centroid_centroid[-1]])

        translation = (translation[0], translation[1], translation[2])

        for i in range(len(part_list)):
            if part_list[i] == 'none':
                continue
            if part_list[i] == 'base' :
                material={
                    'name': 'plastic',
                    'Kd': (0.25, 0.25, 0.25),
                    'Ks': (0.25, 0.25, 0.25),
                    'roughness': 0.9
                }
            else:
                material={
                    'name': 'plastic',
                    'Kd': (colors[i][0], colors[i][1], colors[i][2]),
                    'Ks': (colors[i][0], colors[i][1], colors[i][2]),
                    'roughness': 0.1,
                    'opacity':0.1,
                }

            # obj center of mass
            path_to_mesh = asset_folder / part_list[i]
            renderer.add_tri_mesh( path_to_mesh, 
                                    transforms = [('s', 0.5), 
                                                  ('t', translation)
                                                  ],
                                    material = material)
            obj_id += 1

        if args.ckbd:
            # use checkerboard rendering
            renderer.add_tri_mesh(asset_root / 'mesh/flat_ground.obj',
            texture_img='chkbd_64_0.7',
            transforms=[
                    ('s', 16.),
                    ('t', (0, 0, min_z))
                ])
        else:
            # white background
            renderer.add_tri_mesh(asset_root / 'mesh/flat_ground.obj',
            texture_img='grid.png',
            transforms=[
                    ('s', 16.),
                    ('t', (0., 0, -1.))
                ])

        # render
        renderer.render(verbose=True, light_magnitude=light_intensity)

    elif args.export_video:
        # Create a folder to store the information.
        output_folder = Path('motions') / 'video' / args.folder
        create_folder(output_folder, exist_ok = True)

        # The asset folder.
        asset_root = Path(root_path) / 'asset'
        # asset_folder = Path(root_path) / 'asset' / 'motions' / args.folder 
        asset_folder = Path(root_path) / 'asset' / 'motions' / args.folder 
        print(asset_folder)

        

        all_frames = os.listdir(asset_folder)
        num_parts = os.listdir(asset_folder / all_frames[0])
        # get first and last frame scene centroid and move all frames by the centroid of the centroids
        last_frame = all_frames[-1]
        min_bbox = []
        max_bbox = []
        first_scene = trimesh.Scene()
        last_scene = trimesh.Scene()
        for cur_obj in num_parts:
            last_mesh = trimesh.load(asset_folder / str(last_frame) / (cur_obj))
            first_mesh = trimesh.load(asset_folder / str(all_frames[0]) / (cur_obj))
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
        # scale = 0.3
        # scale = 0.5
        scale = 5 / np.linalg.norm(bbox)
        min_z *= scale
        translation = np.array([-2, 4, 4]) - np.array([0, 0, centroid_centroid[-1]*scale])
        translation = (translation[0], translation[1], translation[2])
        min_z += translation[2]
        print('minz', min_z)


        for frame in all_frames:
            idx = int(frame)
            jitter = np.array([[0, 0, 0] for _ in range(len(num_parts))] )
            # if idx == 0:
            #     jitter = np.random.randn(len(num_parts), 3)
            #     jitter[0] = np.array([0., 0., 0.])
            out_file_name =  str(output_folder / ('{}_{:04d}.png'.format(args.folder, idx)))
        
            # Create the render.
            options = {
                'file_name': out_file_name,
                # 'light_map': 'uffizi-large.exr',
                'light_map':'lightmap.exr',
                # 'resolution': (1200, 1200),
                'resolution': (720, 720),
                # 'resolution': (240, 240),
                # 'sample': 8,
                'sample': 128,
                'max_depth': 6,
                # 'camera_pos': (12.5, -12, 12.1), # uffizi
                'camera_pos': (-12+5, 20-5, 12), # lightmap
                # 'camera_pos': (10, 10, 12.1),
                # 'camera_lookat': (0.3+0.1, 0, -0.4+0.1),
                'camera_lookat' :(0, 0, 0),
                # 'camera_lookat': (0.15, 0, -0.2),
                'camera_up': (0, 0, 1),
                
            }

            renderer = PbrtRenderer(options)

            # part_list = ['0', '1' ] #, '2', '3', '4', 'none']
            part_list = os.listdir(asset_folder / str(all_frames[0]) )
            print(part_list)
            factor = 5.0 #3.5 # 2.5 
            light_intensity = 8.0 # 0.8 
            delta1 = 30
            delta2 = 40
            color_wheel = [np.array([107, 166+delta1, 161+delta1]), np.array([209+delta2, 184+delta1, 148]), np.array([183, 192, 182]), np.array([81, 90, 63]), np.array([220, 203, 182]), np.array([150, 132, 117]), np.array([111, 119, 113])] * 20
            colors = [x/(factor*255) for x in color_wheel]
            # Add meshes to the scene.
            obj_id = 0
            # translation = np.array([2, -2, 4]) - np.array([0, 0, centroid_centroid[-1]*scale])
            translation = np.array([-2, 4, 4]) - np.array([0, 0, centroid_centroid[-1]*scale])
            translation = (translation[0], translation[1], translation[2]) 
            # print('translation[2]', translation[2])
            for i in range(len(part_list)):
                if part_list[i] == 'none':
                    continue
                if part_list[i] == '' :
                    print('part_list[i]', part_list[i])
                    material={
                        'name': 'translucent',
                        'Kd': (colors[i][0], colors[i][1], colors[i][2]),
                        'Ks': (colors[i][0], colors[i][1], colors[i][2]),
                        'reflect': 0.5,
                        'transmit': 0.9,
                        'roughness': 0.5,
                    }
                else:
                    material={
                        'name': 'plastic',
                        'Kd': (colors[i][0], colors[i][1], colors[i][2]),
                        'Ks': (colors[i][0], colors[i][1], colors[i][2]),
                        'roughness': 0.1,
                    }

                renderer.add_tri_mesh(asset_folder / str(frame) / part_list[i], 
                                        transforms = [('s', scale), 
                                                        ('r', (math.pi*2, 0, 0, 1)),
                                                        ('t', translation + jitter)],
                                        material = material)
                obj_id += 1
            
            if args.ckbd:
                # use checkerboard rendering
                renderer.add_tri_mesh(asset_root / 'mesh/flat_ground.obj',
                                    texture_img='chkbd_64_0.7',
                                    transforms=[
                                            ('s', 16.),
                                            ('t', (0, 0, min_z))
                                        ])
            else:
                renderer.add_tri_mesh(asset_root / 'mesh/flat_ground.obj',
                                    texture_img='grid.png',
                                    transforms=[
                                            ('s', 16.),
                                            ('t', (0., 0, -1.))
                                        ])

            # render
            renderer.render(light_magnitude=light_intensity)

            if args.no_bg:
                img = Image.open(out_file_name.replace('png', 'jpeg')).convert('RGBA');
                datas = img.getdata()
                new_data = []
                white_thresh = 230
                for item in datas:
                    if item[0] >= white_thresh and item[1] >= white_thresh and item[2] >= white_thresh:
                        new_data.append((255, 255, 255, 0))
                    else:
                        new_data.append(item)
                img.putdata(new_data)
                img.save( str(output_folder / ('{}_{:04d}_new.png'.format(args.folder, idx))))

            ## Print progress.
            print_info('{:d}/{:d} done...'.format(idx, len(all_frames)))
        # Export to mp4.
        if not args.overlay:
            export_mp4_jpeg(output_folder, output_folder / 'demo.mp4', fps=fps)
            print_info('Please open {} to see the video'.format(output_folder / 'demo.mp4'))
        elif args.no_video:
            print('not exporting video')
        else:
            overlay(args)
    
    elif args.overlay:
        overlay(args)
    
    else:
        print(' function not defined')
    
    

