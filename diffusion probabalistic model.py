import torch
import torch.nn as nn
import numpy as np
import cv2
from random import randint as rnd
from torch.nn import functional as F






frame = cv2.imread("deleted.jpg")

frame_height = frame.shape[0]
frame_width = frame.shape[1]

for_i=[]
for_j=[]

for i in range(frame_height):
    for j in range(frame_width):
        for k in range(0,3):
            if frame[i][j][k]==0:
                for_i.append(i)
                for_j.append(j)

ii = np.round(np.mean(for_i))
jj = np.round(np.mean(for_j))

ii = ii.astype(np.int32)
jj = jj.astype(np.int32)

frame_1=frame[0:ii,0:jj]

frame_height_1 = frame_1.shape[0]
frame_width_1 = frame_1.shape[1]

f_i = []
f_j = []

rand_i = []
rand_j = []

for i in range(frame_height_1):
    for j in range(frame_width_1):
        for k in range(3):
            if frame_1[i][j][k] == 0:
                f_i.append(i-300)
                f_j.append(j-300)

                idx_i=rnd(0,np.max(f_i))
                idx_j=rnd(0,np.max(f_j))

                rand_i.append(idx_i)
                rand_j.append(idx_j)

rand_i=np.array(rand_i)
rand_j=np.array(rand_j)



class LatentEmbedding(nn.Module):

    def __init__(
        self, data_shape: tuple, head: nn.Module, backbone: nn.Module
    ):
        super().__init__()

        self.data_shape = data_shape
        self.head = head
        self.backbone = backbone

        for param in self.backbone.parameters():
            param.requires_grad = False

    def forward(self, x):

        B = x.size(0)

        z = self.backbone(x)
        z_unflatten = z.view(B, 1, 1, 1)
        z_residual = self.head(z_unflatten)

        return z + z_residual.view(B, -1)


class head(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.LazyConv2d(len(rand_i), (1, 1), bias=False)

    def forward(self, x):
        c = self.conv(x)

        return c

res = head()

class backbone(nn.Module):
    def __init__(self):
        super().__init__()

        self.tanh = nn.Tanh()

    def forward(self, x):
        s = self.tanh(x)
        return s


b = backbone()

rand_i = torch.from_numpy(rand_i)
rand_j = torch.from_numpy(rand_j)

l_e = LatentEmbedding(rand_i.shape, res, b)


l_i = l_e(rand_i)
l_j = l_e(rand_j)


mean, std_dev = 0, 25

for_gauss = []
for i in range(frame_height_1):
    for j in range(frame_width_1):
        for k in range(3):
            if frame_1[i][j][k] == 0:
                for_gauss = np.append(for_gauss, frame_1[i][j][k])

mean,std_dev=0,25
gaussian_noise = np.random.normal(mean, std_dev, for_gauss.shape)

dst = cv2.add(np.array(for_gauss), gaussian_noise)

probably_denoised = frame_1[300:500]

beta_1 = 0.05
beta_0 = 0.1

probably_denoised = probably_denoised.reshape(408000)

marginal_log_mean_coeffs_noised = (
    -0.25 * dst**2 * (beta_1 - beta_0) - 0.5 * dst * beta_0
)

marginal_log_mean_coeffs_noised = torch.from_numpy(
    marginal_log_mean_coeffs_noised
)

marginal_log_mean_coeffs_denoised = (
    -0.25 * probably_denoised**2 * (beta_1 - beta_0)
    - 0.5 * probably_denoised * beta_0
)

marginal_log_mean_coeffs_denoised = torch.from_numpy(
    marginal_log_mean_coeffs_denoised
)

log_std_t = 0.5 * torch.log(1 - torch.exp(2 * marginal_log_mean_coeffs_noised))

# # marginal_lambda_1
marginal_lambda_t = marginal_log_mean_coeffs_noised - log_std_t

log_std_s = 0.5 * torch.log(
    1 - torch.exp(2 * marginal_log_mean_coeffs_denoised)
)

# # # # marginal lambda 2
marginal_lambda_s = marginal_log_mean_coeffs_denoised - log_std_s


marginal_std_s = torch.sqrt(1 - torch.exp(2 * marginal_log_mean_coeffs_noised))

marginal_std_t = torch.sqrt(
    1 - torch.exp(2 * marginal_log_mean_coeffs_denoised)
)


def find_h(start_i, end_i, dst, coeffs):
    beta_1 = 0.05
    beta_0 = 0.1

    if start_i >= end_i:
        return np.empty((0, 1))

    dst_slice = dst[start_i:end_i]

    if start_i < coeffs.shape[0]:
        end_idx = min(end_i, coeffs.shape[0])
        coeffs_slice = coeffs[start_i:end_idx]
    else:

        coeffs_slice = np.zeros_like(dst_slice)

    if coeffs_slice.shape != dst_slice.shape:
        if coeffs_slice.ndim > dst_slice.ndim:

            coeffs_slice = coeffs_slice[:, 0, 0].reshape(-1, 1)
        elif coeffs_slice.ndim < dst_slice.ndim:
            coeffs_slice = coeffs_slice.reshape(-1, 1)

    denoised = (
        -0.25 * dst_slice**2 * (beta_1 - beta_0) - 0.5 * dst_slice * beta_0
    )
    zeros = np.zeros(np.abs(len(coeffs_slice) - len(denoised)))
    denoised = np.append(denoised, zeros)
    denoised = torch.from_numpy(denoised)
    h_out = denoised - coeffs_slice
    return h_out


ranges = [
    (0, (len(dst) // 5) - 17),
    ((len(dst) // 5) - 17, ((len(dst) // 5) - 17) * 2),
    (((len(dst) // 5) - 17) * 2, ((len(dst) // 5) - 17) * 3),
    (((len(dst) // 5) - 17) * 3, ((len(dst) // 5) - 17) * 4),
    (((len(dst) // 5) - 17) * 4, ((len(dst) // 5) - 17) * 5),
    (((len(dst) // 5) - 17) * 5, len(dst))
]

h_parts=[]

for start_i, end_i in ranges:
    h = find_h(start_i, end_i, dst, marginal_log_mean_coeffs_denoised)
    # h_parts.append(h)

# h=np.concatenate(h_parts)

def model_fn(x, noise, sigma_t, alpha_t):

    eps = 1e-12

    x = np.asarray(x, dtype=np.float64).reshape(-1)
    noise = np.asarray(noise, dtype=np.float64).reshape(-1)

    sigma_t = np.asarray(
        (
            sigma_t.detach().cpu().numpy()
            if torch.is_tensor(sigma_t)
            else sigma_t
        ),
        dtype=np.float64,
    ).reshape(-1)

    alpha_t = np.asarray(
        (
            alpha_t.detach().cpu().numpy()
            if torch.is_tensor(alpha_t)
            else alpha_t
        ),
        dtype=np.float64,
    ).reshape(-1)

    sigma_t = np.nan_to_num(sigma_t, nan=eps, posinf=eps, neginf=eps)
    alpha_t = np.nan_to_num(alpha_t, nan=eps, posinf=eps, neginf=eps)

    alpha_t[alpha_t == 0] = eps

    if len(noise) < len(sigma_t):
        zeros = np.zeros(len(sigma_t) - len(noise))
        noise = np.concatenate([noise, zeros])

    noise = noise[: len(sigma_t)]
    x = x[: len(sigma_t)]

    sigma_out = sigma_t * noise

    minus = x - sigma_out

    x0 = minus / (alpha_t + eps)

    x0 = np.nan_to_num(x0, nan=0.0, posinf=0.0, neginf=0.0)

    return x0


def probabilistic_solver(rand_i, rand_j, r1=1 / 3, r2=2 / 3, h=h):

    eps = 1e-12

    sigma_t = np.asarray(
        (
            marginal_std_t.detach().cpu().numpy()
            if torch.is_tensor(marginal_std_t)
            else marginal_std_t
        ),
        dtype=np.float64,
    ).reshape(-1)

    sigma_s = np.asarray(
        (
            marginal_std_s.detach().cpu().numpy()
            if torch.is_tensor(marginal_std_s)
            else marginal_std_s
        ),
        dtype=np.float64,
    ).reshape(-1)

    alpha_t = torch.exp(marginal_log_mean_coeffs_denoised)

    alpha_t = np.asarray(
        (
            alpha_t.detach().cpu().numpy()
            if torch.is_tensor(alpha_t)
            else alpha_t
        ),
        dtype=np.float64,
    ).reshape(-1)

    rand_i = np.asarray(rand_i, dtype=np.float64).reshape(-1)
    rand_j = np.asarray(rand_j, dtype=np.float64).reshape(-1)

    sigma_t = np.nan_to_num(sigma_t, nan=eps)
    sigma_s = np.nan_to_num(sigma_s, nan=eps)

    sigma_s[sigma_s == 0] = eps

    alpha_t = np.nan_to_num(alpha_t, nan=eps)
    alpha_t[alpha_t == 0] = eps

    sigma_div = sigma_t[:len(rand_i)] / (sigma_s[:len(rand_i)] + eps)

    sigma_div = np.nan_to_num(sigma_div, nan=0.0, posinf=0.0, neginf=0.0)

    phi_1 = torch.expm1(r1 * h)

    phi_1 = np.asarray(
        phi_1.detach().cpu().numpy() if torch.is_tensor(phi_1) else phi_1,
        dtype=np.float64,
    ).reshape(-1)

    if len(phi_1) < len(alpha_t):
        zeros = np.zeros(len(alpha_t) - len(phi_1))
        phi_1 = np.concatenate([phi_1, zeros])

    phi_1 = phi_1[: len(alpha_t)]

    model_s = model_fn(probably_denoised, gaussian_noise, sigma_t, alpha_t)

    a = alpha_t * phi_1

    a = np.nan_to_num(a, nan=0.0)

    sigma_i = sigma_div * rand_i[: len(sigma_div)]

    sigma_j = sigma_div * rand_j[: len(sigma_div)]

    sigma_i = np.nan_to_num(sigma_i, nan=0.0)
    sigma_j = np.nan_to_num(sigma_j, nan=0.0)

    am = model_s[: len(a)] * a

    am = np.nan_to_num(am, nan=0.0)

    x_i = r1 * (sigma_i * am[: len(sigma_i)]) + r2 * (
        sigma_i * am[: len(sigma_i)]
    )

    x_j = r1 * (sigma_j * am[: len(sigma_j)]) + r2 * (
        sigma_j * am[: len(sigma_j)]
    )

    x_i = np.nan_to_num(x_i, nan=0.0, posinf=0.0, neginf=0.0)

    x_j = np.nan_to_num(x_j, nan=0.0, posinf=0.0, neginf=0.0)

    return x_i, x_j


probabilities1, probabilities2 = probabilistic_solver(rand_i, rand_j)

probabilities1 = expit(probabilities1)
probabilities2 = expit(probabilities2)

eps = 1e-12

probabilities1 = np.clip(probabilities1, eps, 1 - eps)

probabilities2 = np.clip(probabilities2, eps, 1 - eps)

rand_i = rand_i.detach().numpy()
rand_j = rand_j.detach().numpy()

indexes_i = (probabilities1 * rand_i).astype(np.int32)
indexes_j = (probabilities2 * rand_j).astype(np.int32)

indexes_i = np.clip(indexes_i, 0, frame_height_1 - 1)
indexes_j = np.clip(indexes_j, 0, frame_width_1 - 1)

counter = 0
num_indexes = len(indexes_i)

for i in range(frame_height_1):
    for j in range(frame_width_1):


        if np.all(frame_1[i, j] == 0):

            idx = indexes_i[counter % num_indexes]
            idy = indexes_j[counter % num_indexes]

            frame_1[i, j] = frame_1[idx, idy]

            counter += 1

cv2.imshow('deleted', frame_1)
cv2.waitKey(0)
