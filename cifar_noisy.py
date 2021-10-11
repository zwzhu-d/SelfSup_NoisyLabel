from __future__ import print_function
from PIL import Image
import os
import os.path
import numpy as np
import sys
import copy
if sys.version_info[0] == 2:
    import cPickle as pickle
else:
    import pickle
import torch
import torch.utils.data as data
from utils import download_url, check_integrity, noisify, noisify_instance

class CIFAR10_noisy(data.Dataset):
    """`CIFAR10 <https://www.cs.toronto.edu/~kriz/cifar.html>`_ Dataset.

    Args:
        root (string): Root directory of dataset where directory
            ``cifar-10-batches-py`` exists or will be saved to if download is set to True.
        train (bool, optional): If True, creates dataset from training set, otherwise
            creates from test set.
        transform (callable, optional): A function/transform that  takes in an PIL image
            and returns a transformed version. E.g, ``transforms.RandomCrop``
        target_transform (callable, optional): A function/transform that takes in the
            target and transforms it.
        download (bool, optional): If true, downloads the dataset from the internet and
            puts it in root directory. If dataset is already downloaded, it is not
            downloaded again.

    """
    base_folder = 'cifar-10-batches-py'
    url = "https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz"
    filename = "cifar-10-python.tar.gz"
    tgz_md5 = 'c58f30108f718f92721af3b95e74349a'
    train_list = [
        ['data_batch_1', 'c99cafc152244af753f735de768cd75f'],
        ['data_batch_2', 'd4bba439e000b95fd0a9bffe97cbabec'],
        ['data_batch_3', '54ebc095f3ab1f0389bbae665268c751'],
        ['data_batch_4', '634d18415352ddfa80567beed471001a'],
        ['data_batch_5', '482c414d41f54cd18b22e5b47cb7c3cb'],
    ]

    test_list = [
        ['test_batch', '40351d587109b95175f43aff81a1287e'],
    ]

    def __init__(self, root, train=True,indexes=None,
                 transform=None, target_transform=None,
                 download=False,down_sample=False,
                 noise_type=None, noise_rate=0.2, random_state=0):
        self.root = os.path.expanduser(root)
        self.transform = transform
        self.target_transform = target_transform
        self.train = train  # training set or test set
        self.dataset='cifar10'
        self.noise_type=noise_type
        self.nb_classes=10
        idx_each_class_noisy = [[] for i in range(10)]
        #if download:
        #    self.download()

        #if not self._check_integrity():
        #    raise RuntimeError('Dataset not found or corrupted.' +
        #                       ' You can use download=True to download it')

        # now load the picked numpy arrays
        if self.train:
            self.train_data = []
            self.train_labels = []
            for fentry in self.train_list:
                f = fentry[0]
                file = os.path.join(self.root, self.base_folder, f)
                fo = open(file, 'rb')
                if sys.version_info[0] == 2:
                    entry = pickle.load(fo)
                else:
                    entry = pickle.load(fo, encoding='latin1')
                self.train_data.append(entry['data'])
                if 'labels' in entry:
                    self.train_labels += entry['labels']
                else:
                    self.train_labels += entry['fine_labels']
                fo.close()
            self.true_labels = copy.deepcopy(self.train_labels)
            self.train_data = np.concatenate(self.train_data)
            self.train_data = self.train_data.reshape((50000, 3, 32, 32))
            self.train_data = self.train_data.transpose((0, 2, 3, 1))  # convert to HWC
            #if noise_type is not None:
            if noise_type !='clean':
                # noisify train data
                if noise_type != 'instance':
                    self.train_labels=np.asarray([[self.train_labels[i]] for i in range(len(self.train_labels))])
                    self.train_noisy_labels, self.actual_noise_rate = noisify(dataset=self.dataset, train_labels=self.train_labels, noise_type=noise_type, noise_rate=noise_rate, random_state=random_state, nb_classes=self.nb_classes)
                    self.train_noisy_labels=[i[0] for i in self.train_noisy_labels]
                    _train_labels=[i[0] for i in self.train_labels]
                    for i in range(len(_train_labels)):
                        idx_each_class_noisy[self.train_noisy_labels[i]].append(i)
                    class_size_noisy = [len(idx_each_class_noisy[i]) for i in range(10)]
                    self.noise_prior = np.array(class_size_noisy)/sum(class_size_noisy)
                    print(f'The noisy data ratio in each class is {self.noise_prior}')
                    self.noise_or_not = np.transpose(self.train_noisy_labels)!=np.transpose(_train_labels)
                else:
                    self.train_noisy_labels, self.actual_noise_rate = noisify_instance(self.train_data, self.train_labels,noise_rate=noise_rate)
                    #self.train_noisy_labels, self.actual_noise_rate = noisify_instance_new(self.train_data, self.train_labels,noise_rate=noise_rate)
                    print('over all noise rate is ', self.actual_noise_rate)
                    #self.train_noisy_labels=[i[0] for i in self.train_noisy_labels]
                    #self.train_noisy_labels=[i[0] for i in self.train_noisy_labels]
                    #_train_labels=[i[0] for i in self.train_labels]
                    for i in range(len(self.train_labels)):
                        idx_each_class_noisy[self.train_noisy_labels[i]].append(i)
                    class_size_noisy = [len(idx_each_class_noisy[i]) for i in range(10)]
                    self.noise_prior = np.array(class_size_noisy)/sum(class_size_noisy)
                    print(f'The noisy data ratio in each class is {self.noise_prior}')
                    self.noise_or_not = np.transpose(self.train_noisy_labels)!=np.transpose(self.train_labels)

                #self.train_noisy_labels = list(torch.load('CIFAR-10_human.pt')['worse_label'])

                if indexes is not None:
                    self.train_data = self.train_data[indexes]
                    self.train_noisy_labels = list(np.array(self.train_noisy_labels)[indexes])
                    self.true_labels = list(np.array(self.true_labels)[indexes])
                if down_sample:
                    count_number =[]
                    for i in range(self.nb_classes):
                        idxs = np.where(np.array(self.train_noisy_labels) == i)[0]
                        count_number.append(len(idxs))
                    min_num = min(count_number)
                    train_labeled_idxs = []
                    for i in range(self.nb_classes):
                        idxs = np.where(np.array(self.train_noisy_labels) == i)[0]
                        np.random.shuffle(idxs)
                        train_labeled_idxs.extend(idxs[:min_num])
                    np.random.shuffle(train_labeled_idxs)
                    

                    self.train_data = self.train_data[train_labeled_idxs]
                    self.train_labels = list(np.array(self.train_labels)[train_labeled_idxs])
                    self.train_noisy_labels = list(np.array(self.train_noisy_labels)[train_labeled_idxs])
                    self.true_labels = list(np.array(self.true_labels)[train_labeled_idxs])

        else:
            f = self.test_list[0][0]
            file = os.path.join(self.root, self.base_folder, f)
            fo = open(file, 'rb')
            if sys.version_info[0] == 2:
                entry = pickle.load(fo)
            else:
                entry = pickle.load(fo, encoding='latin1')
            self.test_data = entry['data']
            if 'labels' in entry:
                self.test_labels = entry['labels']
            else:
                self.test_labels = entry['fine_labels']
            fo.close()
            self.test_data = self.test_data.reshape((10000, 3, 32, 32))
            self.test_data = self.test_data.transpose((0, 2, 3, 1))  # convert to HWC

    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            tuple: (image, target) where target is index of the target class.
        """
        if self.train:
            if self.noise_type !='clean':
                img, target = self.train_data[index], self.train_noisy_labels[index]
            else:
                img, target = self.train_data[index], self.train_labels[index]
        else:
            img, target = self.test_data[index], self.test_labels[index]

        # doing this so that it is consistent with all other datasets
        # to return a PIL Image
        img = Image.fromarray(img)

        if self.transform is not None:
            img = self.transform(img)

        if self.target_transform is not None:
            target = self.target_transform(target)
        true_target = self.true_labels[index]
        return img, target, true_target, index

    def __len__(self):
        if self.train:
            return len(self.train_data)
        else:
            return len(self.test_data)

    def _check_integrity(self):
        root = self.root
        for fentry in (self.train_list + self.test_list):
            filename, md5 = fentry[0], fentry[1]
            fpath = os.path.join(root, self.base_folder, filename)
            if not check_integrity(fpath, md5):
                return False
        return True

    def download(self):
        import tarfile

        if self._check_integrity():
            print('Files already downloaded and verified')
            return

        root = self.root
        download_url(self.url, root, self.filename, self.tgz_md5)

        # extract file
        cwd = os.getcwd()
        tar = tarfile.open(os.path.join(root, self.filename), "r:gz")
        os.chdir(root)
        tar.extractall()
        tar.close()
        os.chdir(cwd)

    def __repr__(self):
        fmt_str = 'Dataset ' + self.__class__.__name__ + '\n'
        fmt_str += '    Number of datapoints: {}\n'.format(self.__len__())
        tmp = 'train' if self.train is True else 'test'
        fmt_str += '    Split: {}\n'.format(tmp)
        fmt_str += '    Root Location: {}\n'.format(self.root)
        tmp = '    Transforms (if any): '
        fmt_str += '{0}{1}\n'.format(tmp, self.transform.__repr__().replace('\n', '\n' + ' ' * len(tmp)))
        tmp = '    Target Transforms (if any): '
        fmt_str += '{0}{1}'.format(tmp, self.target_transform.__repr__().replace('\n', '\n' + ' ' * len(tmp)))
        return fmt_str
