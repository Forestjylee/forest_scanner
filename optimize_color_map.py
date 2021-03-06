import argparse
import numpy as np
import open3d as o3d
from os import getcwd
from os.path import join, exists
from utils import get_rgbd_file_lists


voxel_size = 0.0025
max_correspondence_distance_coarse = voxel_size * 15
max_correspondence_distance_fine = voxel_size * 1.5


def load_point_clouds_and_rgbd_images(dataset_folder, voxel_size):
    color_files, depth_files = get_rgbd_file_lists(dataset_folder)
    pcds = []
    rgbd_images = []
    for i in range(len(depth_files)):
        depth = o3d.io.read_image(depth_files[i])
        color = o3d.io.read_image(color_files[i])
        rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
            color, depth, 
            depth_trunc=1.0,
            convert_rgb_to_intensity=False)
        pcd = o3d.geometry.PointCloud.create_from_rgbd_image(
        rgbd_image,
        o3d.camera.PinholeCameraIntrinsic(o3d.io.read_pinhole_camera_intrinsic(join(dataset_folder, "camera_intrinsic.json"))))
        pcd_down = pcd.voxel_down_sample(voxel_size=voxel_size)
        pcd_down.estimate_normals()
        pcds.append(pcd_down)
        rgbd_images.append(rgbd_image)
    return pcds, rgbd_images


def generate_camera_trajectory(camera_intrinsic, pose_graph):
    camera_trajectory = o3d.camera.PinholeCameraTrajectory()
    params_list = []
    for node in pose_graph.nodes:
        camera_params = o3d.camera.PinholeCameraParameters()
        camera_params.intrinsic = camera_intrinsic
        camera_params.extrinsic = np.linalg.inv(node.pose)
        params_list.append(camera_params)
    camera_trajectory.parameters = params_list
    return camera_trajectory


def color_map_optimization(mesh, rgbd_images, camera_trajectory, maximum_iteration=200):
    option = o3d.color_map.ColorMapOptimizationOption()
    option.maximum_iteration = maximum_iteration
    option.non_rigid_camera_coordinate = False
    o3d.color_map.color_map_optimization(mesh, rgbd_images, camera_trajectory, option)
    return mesh

if __name__ == "__main__":
    o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Debug)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--dataset", type=str,
        help="Dataset that saves color images, depth images and camera intrinsic.", default=join(getcwd(), "dataset"))
    args = parser.parse_args()
    if not exists(args.dataset):
        print("Dataset is not exist, please check your input.")
        exit(-1)

    dataset_folder = args.dataset
    camera_intrinsic = o3d.io.read_pinhole_camera_intrinsic(join(dataset_folder, "camera_intrinsic.json"))
    pose_graph = o3d.io.read_pose_graph(join(dataset_folder, "pose_graph.json"))
    camera_trajectory = generate_camera_trajectory(camera_intrinsic, pose_graph)   
    
    mesh = o3d.io.read_triangle_mesh(join(dataset_folder, "online_raw_mesh.ply"))
    pcds_down, rgbd_images = load_point_clouds_and_rgbd_images(dataset_folder, voxel_size)

    mesh = color_map_optimization(mesh, rgbd_images, camera_trajectory, 200)
    o3d.io.write_triangle_mesh(join(dataset_folder, "online_optimized_mesh.ply"), mesh, False)