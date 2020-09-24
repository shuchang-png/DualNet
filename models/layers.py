from __future__ import absolute_import, division, print_function

import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F

from torch.nn import BatchNorm2d as bn


class SSIM(nn.Module):
    def __init__(self):
        super(SSIM, self).__init__()
        self.mu_x_pool   = nn.AvgPool2d(3, 1)
        self.mu_y_pool   = nn.AvgPool2d(3, 1)
        self.sig_x_pool  = nn.AvgPool2d(3, 1)
        self.sig_y_pool  = nn.AvgPool2d(3, 1)
        self.sig_xy_pool = nn.AvgPool2d(3, 1)
        self.refl = nn.ReflectionPad2d(1)
        self.C1 = 0.01 ** 2
        self.C2 = 0.03 ** 2

    def forward(self, x, y):
        x = self.refl(x)
        y = self.refl(y)
        mu_x = self.mu_x_pool(x)
        mu_y = self.mu_y_pool(y)
        sigma_x  = self.sig_x_pool(x ** 2) - mu_x ** 2
        sigma_y  = self.sig_y_pool(y ** 2) - mu_y ** 2
        sigma_xy = self.sig_xy_pool(x * y) - mu_x * mu_y
        SSIM_n = (2 * mu_x * mu_y + self.C1) * (2 * sigma_xy + self.C2)
        SSIM_d = (mu_x ** 2 + mu_y ** 2 + self.C1) * (sigma_x + sigma_y + self.C2)
        return torch.clamp((1 - SSIM_n / SSIM_d) / 2, 0, 1)


def upsample(x):
    return F.interpolate(x, scale_factor=2, mode="nearest")


def upshuffle(in_planes, upscale_factor):
    return nn.Sequential(
        nn.ReflectionPad2d(1),
        nn.Conv2d(in_planes, in_planes*upscale_factor**2, kernel_size=3, stride=1, padding=0),
        nn.PixelShuffle(upscale_factor),
        nn.ELU(inplace=True)
    )


class DeconvBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(DeconvBlock, self).__init__()
        self.conv = nn.ConvTranspose2d(in_channels, out_channels, kernel_size=3, stride=2, padding=1, output_padding=0)
        self.pad = nn.ReflectionPad2d((0, 1, 0, 1))
        self.nonlin = nn.ELU(inplace=True)
    def forward(self, x):
        out = self.conv(x)
        out = self.pad(out)
        out = self.nonlin(out)
        return out


class ConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ConvBlock, self).__init__()
        self.conv = Conv3x3(in_channels, out_channels)
        self.nonlin = nn.ELU(inplace=True)
    def forward(self, x):
        out = self.conv(x)
        out = self.nonlin(out)
        return out


class Conv1x1(nn.Module):
    def __init__(self, in_channels, out_channels, bias=False):
        super(Conv1x1, self).__init__()
        self.conv = nn.Conv2d(int(in_channels), int(out_channels), kernel_size=1, stride=1, bias=bias)
    def forward(self, x):
        out = self.conv(x)
        return out


class Conv3x3(nn.Module):
    def __init__(self, in_channels, out_channels, use_refl=True):
        super(Conv3x3, self).__init__()
        if use_refl:
            self.pad = nn.ReflectionPad2d(1)
        else:
            self.pad = nn.ZeroPad2d(1)
        self.conv = nn.Conv2d(int(in_channels), int(out_channels), 3)
        self.bn = bn(int(out_channels))
    def forward(self, x):
        out = self.pad(x)
        out = self.conv(out)
        out = self.bn(out)
        out = F.leaky_relu(out)
        return out

