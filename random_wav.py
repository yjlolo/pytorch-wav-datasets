import os
import numpy as np
import random
import torch
from torch.utils.data import Dataset
from tqdm import tqdm
import torchaudio


class RandomWAVDataset(Dataset):
    """
    Wave-file-only Dataset.
    """

    def __init__(self,
                 data_dir: str,
                 size: int,
                 segment: int,
                 deterministic: bool = True):
        self.segment = segment
        self.data_path = os.path.expanduser(data_dir)
        self.size = size
        self.determanistic = deterministic

        self.waves = []
        self.sr = None
        self.files = []

        file_lengths = []

        print("Gathering training files ...")
        for f in tqdm(sorted(os.listdir(self.data_path))):
            if f.endswith('.wav'):
                filename = os.path.join(self.data_path, f)
                meta = torchaudio.info(filename)
                self.files.append(filename)
                file_lengths.append(max(0, meta.num_frames - segment) + 1)

                if not self.sr:
                    self.sr = meta.sample_rate
                else:
                    assert meta.sample_rate == self.sr

        self.file_lengths = np.array(file_lengths)
        self.boundaries = np.cumsum(
            np.array([0] + file_lengths)) / self.file_lengths.sum()

    def __len__(self):
        return self.size

    def __getitem__(self, index):
        if self.determanistic:
            uniform_pos = random.uniform(0, 1)
        else:
            uniform_pos = index / self.size
        bin_pos = np.digitize(uniform_pos, self.boundaries[1:], right=False)
        f, length = self.files[bin_pos], self.file_lengths[bin_pos]
        offset = int(length * (uniform_pos - self.boundaries[bin_pos]) / (
            self.boundaries[bin_pos+1] - self.boundaries[bin_pos]))
        x = torchaudio.load(f, frame_offset=offset,
                            num_frames=self.segment)[0].mean(0)

        # this should not happen but I just want to make sure
        if x.numel() < self.segment:
            x = torch.cat([x, x.new_zeros(self.segment - x.numel())])
        return x