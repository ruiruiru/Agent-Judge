# Table 2. Efficiency and complexity

Environment-specific measurements only: B2 used CPU and B4 used CUDA on an NVIDIA GeForce RTX 5070. No cross-target AP comparison is implied.

| Method | Representation | Dim. | Measured device | Warm extraction / traj. | Classifier inference / traj. | Representation storage | Classifier | Encoder | Peak CPU RSS | Peak GPU VRAM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B2 | frozen structural full13 | 13 | CPU | 0.01343 ms | 0.0007026 ms | 20.0 KiB | 1.16 KiB | NA | 155 MiB | NA |
| B4 | frozen Qwen3 dense semantic | 1024 | CUDA RTX 5070 | 2.37e3 ms | 0.001803 ms | 784 KiB | 8.34 KiB | 1.16e6 KiB | 2.16e3 MiB | 1.54e3 MiB |
