# -*- coding: utf-8 -*-
import os, re, math, pylab
from math import *
import numpy as np
from StringIO import StringIO
from PIL import Image
from chainer import cuda, Variable, function
from chainer.utils import type_check

def load_images(args, convert_to_grayscale=True):
	dataset = []
	fs = os.listdir(args.image_dir)
	print "loading", len(fs), "images..."
	for fn in fs:
		f = open("%s/%s" % (args.image_dir, fn), "rb")
		if convert_to_grayscale:
			img = np.asarray(Image.open(StringIO(f.read())).convert("L"), dtype=np.float32) / 255.0
		else:
			img = np.asarray(Image.open(StringIO(f.read())).convert("RGB"), dtype=np.float32).transpose(2, 0, 1) / 255.0
		img = (img - 0.5) / 0.5
		dataset.append(img)
		f.close()
	return dataset

def load_labeled_images(args, convert_to_grayscale=True):
	dataset = []
	labels = []
	fs = os.listdir(args.image_dir)
	print "loading", len(fs), "images..."
	for fn in fs:
		m = re.match("(.)_.+", fn)
		label = int(m.group(1))
		f = open("%s/%s" % (args.image_dir, fn), "rb")
		if convert_to_grayscale:
			img = np.asarray(Image.open(StringIO(f.read())).convert("L"), dtype=np.float32) / 255.0
		else:
			img = np.asarray(Image.open(StringIO(f.read())).convert("RGB"), dtype=np.float32).transpose(2, 0, 1) / 255.0
		img = (img - 0.5) / 0.5
		dataset.append(img)
		labels.append(label)
		f.close()
	return dataset, labels

def sample_x_variables(batchsize, ndim_x, dataset, sequential=False, use_gpu=True):
	x_batch = np.zeros((batchsize, ndim_x), dtype=np.float32)
	for j in range(batchsize):
		data_index = np.random.randint(len(dataset))
		if sequential:
			data_index = j
		img = dataset[data_index]
		x_batch[j] = img.reshape((ndim_x,))
	x_batch = Variable(x_batch)
	if use_gpu:
		x_batch.to_gpu()
	return x_batch

def sample_x_and_label_variables(batchsize, ndim_x, dataset, sequential=False, use_gpu=True):
	x_batch = np.zeros((batchsize, ndim_x), dtype=np.float32)
	label_batch = np.zeros((batchsize, 1), dtype=np.int32)
	for j in range(batchsize):
		data_index = np.random.randint(len(dataset))
		if sequential:
			data_index = j
		img = dataset[data_index]
		x_batch[j] = img.reshape((ndim_x,))
		label_batch[j] = labels[data_index]
	x_batch = Variable(x_batch)
	if use_gpu:
		x_batch.to_gpu()
	return x_batch, label_batch

def visualize_reconstruction(reconstructed_x_batch, image_width=28, image_height=28, image_channel=1, dir=None):
	if dir is None:
		raise Exception()
	try:
		os.mkdir(dir)
	except:
		pass
	fig = pylab.gcf()
	fig.set_size_inches(16.0, 16.0)
	pylab.clf()
	if image_channel == 1:
		pylab.gray()
	for m in range(100):
		pylab.subplot(10, 10, m + 1)
		if image_channel == 1:
			pylab.imshow(np.clip((reconstructed_x_batch[m] + 1.0) / 2.0, 0.0, 1.0).reshape((image_width, image_height)), interpolation="none")
		elif image_channel == 3:
			pylab.imshow(np.clip((reconstructed_x_batch[m] + 1.0) / 2.0, 0.0, 1.0).reshape((image_channel, image_width, image_height)), interpolation="none")
		pylab.axis("off")
	pylab.savefig("%s/reconstruction.png" % dir)

def visualize_walkthrough():
	x_batch = sample_x_from_data_distribution(20)
	z_batch = gen(x_batch, test=True)
	if use_gpu:
		z_batch.to_cpu()

	fig = pylab.gcf()
	fig.set_size_inches(16.0, 16.0)
	pylab.clf()
	if config.img_channel == 1:
		pylab.gray()
	
	z_a = z_batch.data[:10,:]
	z_b = z_batch.data[10:,:]
	for col in range(10):
		_z_batch = z_a * (1 - col / 9.0) + z_b * col / 9.0
		_z_batch = Variable(_z_batch)
		if use_gpu:
			_z_batch.to_gpu()
		_x_batch = dec(_z_batch, test=True)
		if use_gpu:
			_x_batch.to_cpu()
		for row in range(10):
			pylab.subplot(10, 10, row * 10 + col + 1)
			if config.img_channel == 1:
				pylab.imshow(np.clip((_x_batch.data[row] + 1.0) / 2.0, 0.0, 1.0).reshape((config.img_width, config.img_width)), interpolation="none")
			elif config.img_channel == 3:
				pylab.imshow(np.clip((_x_batch.data[row] + 1.0) / 2.0, 0.0, 1.0).reshape((config.img_channel, config.img_width, config.img_width)), interpolation="none")
			pylab.axis("off")
				
	pylab.savefig("%s/walk_through.png" % args.visualization_dir)

def visualize_labeled_z():
	x_batch, label_batch = sample_x_and_label_from_data_distribution(len(dataset), sequential=True)
	z_batch = gen(x_batch, test=True)
	z_batch = z_batch.data

	fig = pylab.gcf()
	fig.set_size_inches(20.0, 16.0)
	pylab.clf()
	colors = ["#2103c8", "#0e960e", "#e40402","#05aaa8","#ac02ab","#aba808","#151515","#94a169", "#bec9cd", "#6a6551"]
	for n in xrange(z_batch.shape[0]):
		result = pylab.scatter(z_batch[n, 0], z_batch[n, 1], c=colors[label_batch[n]], s=40, marker="o", edgecolors='none')

	classes = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
	recs = []
	for i in range(0, len(colors)):
	    recs.append(mpatches.Rectangle((0, 0), 1, 1, fc=colors[i]))

	ax = pylab.subplot(111)
	box = ax.get_position()
	ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
	ax.legend(recs, classes, loc="center left", bbox_to_anchor=(1.1, 0.5))
	pylab.xticks(pylab.arange(-4, 5))
	pylab.yticks(pylab.arange(-4, 5))
	pylab.xlabel("z1")
	pylab.ylabel("z2")
	pylab.savefig("%s/labeled_z.png" % args.visualization_dir)

class Concat(function.Function):
	def check_type_forward(self, in_types):
		n_in = in_types.size()
		type_check.expect(n_in == 2)
		x_type, label_type = in_types

		type_check.expect(
			x_type.dtype == np.float32,
			label_type.dtype == np.float32,
			x_type.ndim == 2,
			label_type.ndim == 2,
		)

	def forward(self, inputs):
		xp = cuda.get_array_module(inputs[0])
		x, label = inputs
		n_batch = x.shape[0]
		output = xp.empty((n_batch, x.shape[1] + label.shape[1]), dtype=xp.float32)
		output[:,:x.shape[1]] = x
		output[:,x.shape[1]:] = label
		return output,

	def backward(self, inputs, grad_outputs):
		x, label = inputs
		return grad_outputs[0][:,:x.shape[1]], grad_outputs[0][:,x.shape[1]:]

def append_label(x, label):
	return Concat()(x, label)