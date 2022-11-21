import os
import sys

project_base_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.append(project_base_dir)

import numpy as np
import json
import trimesh

import numpy as np
from scipy.spatial.transform import Rotation


def get_transform_matrix(state, com=np.zeros(3)):
    '''
    Get transformation matrix of the given state and center of mass
    '''
    if len(state) == 3: # translation only
        transform = np.eye(4)
        transform[:3, 3] = state
        return transform
    elif len(state) == 6: # translation + rotation
        translation, rotation = state[:3], state[3:]
        rotation = Rotation.from_rotvec(rotation).as_matrix()
        trans0_mat = np.eye(4)
        trans0_mat[:3, 3] = -com
        rot_mat = np.eye(4)
        rot_mat[:3, :3] = rotation
        trans1_mat = np.eye(4)
        trans1_mat[:3, 3] = translation + com
        return trans1_mat.dot(rot_mat).dot(trans0_mat)
    else:
        raise NotImplementedError


def transform_pts_by_matrix(pts, matrix):
    '''
    Transform an array of xyz pts (n, 3) by a 4x4 matrix
    '''
    pts = np.array(pts)
    if len(pts.shape) == 1:
        if len(pts) == 3:
            v = np.append(pts, 1.0)
        elif len(pts) == 4:
            v = pts
        else:
            raise NotImplementedError
        v = matrix @ v
        return v[0:3]
    elif len(pts.shape) == 2:
        # transpose first
        if pts.shape[1] == 3:
            # pad the points with ones to be (n, 4)
            v = np.hstack([pts, np.ones((len(pts), 1))]).T
        elif pts.shape[1] == 4:
            v = pts.T
        else:
            raise NotImplementedError
        v = matrix @ v
        # transpose and crop back to (n, 3)
        return v.T[:, 0:3]
    else:
        raise NotImplementedError


def transform_pts_by_state(pts, state, com=np.zeros(3)):
    matrix = get_transform_matrix(state, com)
    return transform_pts_by_matrix(pts, matrix)

def load_translation(obj_dir, rotvec=None):
    '''
    Load translation from dir
    '''
    coms = None
    translation_path = os.path.join(obj_dir, 'translation.json')
    if rotvec is not None:
        assert len(rotvec) == 3
    if os.path.exists(translation_path):
        with open(translation_path, 'r') as fp:
            coms = json.load(fp)
        new_coms = {}
        for key, val in coms.items():
            new_coms[int(key)] = np.array(val)
            if rotvec is not None:
                new_coms[int(key)] = transform_pts_by_state(new_coms[int(key)], np.concatenate([np.zeros(3), rotvec]))
        coms = new_coms
    return coms


def com_to_transform(com):
    '''
    COM to transformation matrix
    '''
    transform = np.eye(4)
    transform[:3, 3] = com
    return transform


def load_assembly(obj_dir, translate=True, rotvec=None, return_names=False):
    '''
    Load the entire assembly from dir
    '''
    meshes = []
    names = []
    if translate:
        coms = load_translation(obj_dir)
    else:
        coms = None

    obj_ids = []
    for file_name in os.listdir(obj_dir):
        if file_name.endswith('.obj'):
            try:
                obj_id = int(file_name.replace('.obj', ''))
            except:
                continue
            obj_ids.append(obj_id)
    obj_ids = sorted(obj_ids)

    for seq, obj_id in enumerate(obj_ids):
        obj_name = f'{obj_id}.obj'
        obj_path = os.path.join(obj_dir, obj_name)
        mesh = trimesh.load_mesh(obj_path, process=False, maintain_order=True)
        if rotvec is not None:
            assert len(rotvec) == 3
            rot_transform = get_transform_matrix(np.concatenate([np.zeros(3), rotvec]))
            mesh.apply_transform(rot_transform)
        if coms is not None:
            if rotvec is not None:
                coms[obj_id] = transform_pts_by_state(coms[obj_id], np.concatenate([np.zeros(3), rotvec]))
            com_transform = com_to_transform(coms[obj_id])
            mesh.apply_transform(com_transform)
        meshes.append(mesh)
        names.append(obj_name)
    
    if return_names:
        return meshes, names
    else:
        return meshes