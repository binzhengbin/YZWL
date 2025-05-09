import warnings
warnings.filterwarnings('ignore')
import scanpy as sc
import anndata as ad
import pandas as pd
import numpy as np
import spateo as st
import pyvista as pv
pv.start_xvfb()
pv.set_jupyter_backend('trame')

import os
if 'XDG_RUNTIME_DIR' not in os.environ:
    os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-h3c002'
    os.makedirs(os.environ['XDG_RUNTIME_DIR'], exist_ok=True)
    os.chmod(os.environ['XDG_RUNTIME_DIR'], 0o700)

import os
# 设置工作路径
os.chdir('/home/bzheng/project/03_3D_spatial/02_result/heart/')
# 检查当前路径
print("Current working directory:", os.getcwd())

def add_exp_label(adata, embryo_pc, marker):
    pc_index=embryo_pc.point_data["obs_index"].tolist()
    expression = adata[pc_index, marker].X.toarray().flatten()
    norm_expression = expression / expression.max()
    ## 此次可修改绘图颜色，使用归一化的RGB值
    low_color = np.array([0.7, 0.7, 0.7])  # 背景：浅灰色RGB
    high_color = np.array([1.0, 0.0, 0.0])  # 表达颜色：纯红色
    rgb_values = low_color + (high_color - low_color) * norm_expression[:, np.newaxis]
    alpha_values = 0.05 + (1 - 0.05) * norm_expression  # 保持alpha在[0.05, 1]范围
    rgba_array = np.hstack([rgb_values, alpha_values.reshape(-1, 1)])
    embryo_pc.point_data["tissue_rgba"] = rgba_array
    return embryo_pc

def add_celltype_label(adata, embryo_pc, target_celltype):
    is_target = adata.obs['cluster'].values == target_celltype
    rgba = np.empty((len(is_target), 4), dtype=np.float32)
    ## 此次可修改绘图颜色，使用归一化的RGB值，第四列为透明度
    rgba[is_target] = [0.08, 0.17, 0.55, 1.0]
    rgba[~is_target] = [0.7, 0.7, 0.7, 0.3]
    embryo_pc.point_data["tissue_rgba"] = rgba
    return embryo_pc

def plot_3d_pc(adata, pc, mesh, mode, target, output):
    
    ## 读取anndata格式的空间组数据（3D）
    adata = adata
    embryo_pc = pc
    
    ## 读取blender优化后的mesh文件,并修正格式
    mesh_model = mesh
    ## 设置cell ID
    original_ids = np.arange(mesh_model.n_cells, dtype=np.int64)
    mesh_model.cell_data["vtkOriginalCellIds"] = original_ids
    ## 设置Point ID
    original_point_ids = np.arange(mesh_model.n_points, dtype=np.int64)
    mesh_model.point_data["vtkOriginalPointIds"] = original_point_ids
    ## 设置颜色
    rgba_value = [0.8627451, 0.8627451, 0.8627451, 0.6]
    tissue_rgba = np.zeros((mesh_model.n_cells, 4), dtype=np.float32) 
    tissue_rgba[:, :] = rgba_value
    mesh_model.cell_data["tissue_rgba"] = tissue_rgba
    ## 设置Tissue names
    tissue_array = np.full(mesh_model.n_cells, "surface", dtype=object)
    mesh_model.cell_data["tissue"] = tissue_array
    if mode == 'celltype':
        target_pc = add_celltype_label(adata, embryo_pc, target)
    elif mode == 'marker':
        target_pc = add_exp_label(adata, embryo_pc, target)
    else:
        print('mode error')
    st.pl.three_d_plot(
        model=st.tdr.collect_models([mesh_model, target_pc]), 
        key="tissue", 
        model_style=["surface", "points"], 
        opacity=[0.2, 1],
        model_size=4,
        colormap=None,
        show_legend=False,
        show_axes=True,
        jupyter="static",
        cpo="xy",
        window_size=(524, 524),
        background='white',
        plotter_filename = output
    )

## 读取anndata文件
adata = sc.read('/home/bzheng/chicken_embryo_E4.5_full_demo.h5ad')
print(adata.obs.mapped_celltype)

#这里是为了去掉细胞ID中倒数第2个-及其后面的字符
def process_cell_id(cell_id):
    parts = cell_id.split('-')
    if len(parts) >= 3:  # 确保有足够的“-”分隔部分
        return '-'.join(parts[:-2]) + '-' + parts[-2]
    return cell_id 
adata.obs.index = adata.obs.index.map(process_cell_id)
adata.obs

#这里的细胞ID文件是心脏亚类的细胞ID及其亚类clusterID的对应关系表格
user_data = pd.read_csv("/home/bzheng/project/03_3D_spatial/02_result/heart/20250308-recluster/result/E4.5/SP/res0.3/E4.5_cell_cluster_mapping.csv", 
                        header=0, names=["cell_id", "cluster"])
for index, row in user_data.iterrows():
    cell_id = row['cell_id']
    new_cluster = row['cluster']
    if cell_id in adata.obs.index:
        adata.obs.at[cell_id, 'cluster'] = new_cluster
    else:
        print(f"警告：细胞 ID {cell_id} 在 h5ad 文件中未找到")

## 读取点云文件
# embryo_pc = pv.read('../mesh/E4.5/sub_embryo_pc_model.vtk')
embryo_pc, plot_cmap = st.tdr.construct_pc(adata=adata.copy(), spatial_key="spatial", groupby="cluster", key_added="tissue", colormap="rainbow")
embryo_pc
# embryo_pc.pv.write('../mesh/E4.5/sub_embryo_pc_model2.vtk')

## 读取mesh文件
mesh_model = pv.read('/home/bzheng/E4.5_embryo_mesh_model.vtk')
adata.obs["cluster"].unique()

## 当绘制细胞类型分布时（细胞类型应是adata.obs['mapped_celltype']中的其中一个）
plot_3d_pc(adata, embryo_pc, mesh_model, 'celltype', 'E4-5-heart-13', 'E4.5_heart_c13.html')

## 当绘制基因表达分布时（基因应是adata.var_names中的其中一个）
plot_3d_pc(adata, embryo_pc, mesh_model, 'marker', 'gene-TBX20', 'E4.5_TBX20.html')


#循环
# Create an output directory for the plots if it doesn't exist
output_dir = "./seurat_cluster_plots"
os.makedirs(output_dir, exist_ok=True)

# Loop through cell types from 0 to 41
for cell_type in range(42):  # 0 to 41 inclusive
    # Convert cell_type to string
    cell_type_str = str(cell_type)
    
    # Define the output filename
    output_filename = os.path.join(output_dir, f"E4.5_c{cell_type}.html")
    
    # Call the plot_3d_pc function for each cell type
    plot_3d_pc(adata, embryo_pc, mesh_model, 'celltype', cell_type_str, output_filename)
    
    # Print progress
    print(f"Generated plot for cell type {cell_type_str}: {output_filename}")

print(f"All plots have been generated in the '{output_dir}' directory.")



